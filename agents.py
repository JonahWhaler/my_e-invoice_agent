import json
from typing import Text

from llm_agent_toolkit.core.local import Image_to_Text, Text_to_Text  # type: ignore
from llm_agent_toolkit.memory import ChromaMemory  # type: ignore
from llm_agent_toolkit._memory import ShortTermMemory  # type: ignore
from llm_agent_toolkit import ChatCompletionConfig  # type: ignore


RELEVANCY_FILTER_PROMPT = """
You are a grading assistant. Your task is to evaluate the correlation between a user query and a knowledge segment retrieved via semantic search.

Analyze the semantic and contextual relationship between the user query and the knowledge segment.
Provide a score between 0.0 and 1.0 to represent the correlation:
    0.0: Completely unrelated.
    1.0: Perfectly related and fully relevant.
Justify your score with a concise reason.

Input Format:
User Query: "<insert user query here>" Knowledge Segment: "<insert knowledge segment here>"

Output Format (JSON):
{
  "reason": "<string>"
  "score": <float>,
}

Note:
- Return only in JSON format with "reason" and "score" as keys. Nothing else!!!
"""


class RelevancyFilter:

    def __init__(self, core: Text_to_Text, threshold: float = 0.5):
        self.core = core
        self.__threshold = threshold

    @property
    def threshold(self) -> float:
        return self.__threshold

    def evaluate(self, query: str, stack: list[dict]) -> list:
        output = []
        for item in stack:
            knowledge_segment = item["content"]
            augmented_query = (
                f'User Query: "{query}" Knowledge Segment: "{knowledge_segment}"'
            )
            responses = self.core.run(query=augmented_query, context=None)
            content = responses[0]["content"]
            # logger.info("\n<content>%s</content>", content)
            try:
                j_object = json.loads(content)
                output.append(float(j_object["score"]))
            except json.JSONDecodeError:
                pass

        return output

    def select_relevant(self, query: str, stack: list[dict]) -> list:
        output: list[dict] = []
        evaluation_report = self.evaluate(query, stack)
        for score, item in zip(evaluation_report, stack):
            if score > self.threshold:
                output.append(item)

        return output


DREAM_CATCHER_PROMPT = """
You are a grounding validator. Your task is to evaluate the grounding of an LLM response based on the provided context.

Compare the LLM response against the context to determine if the response is factually supported and aligns with the given information.
Provide a score between 0.0 and 1.0:
    0.0: Completely hallucinated or unsupported by the context.
    1.0: Fully grounded in the context and factually accurate.
Justify your score with a concise explanation that highlights specific aspects of the response and context.

Input Format:
LLM Response: "<insert LLM response here>" Context: "<insert context here>"

Output Format (JSON):
{
  "reason": "<string>"
  "score": <float>,
}

Note:
- Return only in JSON format with "reason" and "score" as keys. Nothing else!!!
"""


class DreamCatcher:
    def __init__(self, core: Text_to_Text, threshold: float = 0.5):
        self.core = core
        self.__threshold = threshold

    @property
    def threshold(self) -> float:
        return self.__threshold

    def catch(self, in_responses: list[dict], context: list[dict]):
        res_str = ""
        ctx_str = ""
        for r in in_responses:
            res_str += f'{r["content"]}\n'
        for c in context:
            ctx_str += f'{c["content"]}\n'
        augmented_query = f'LLM Response: "{res_str}" Context: "{ctx_str}"'
        responses = self.core.run(query=augmented_query, context=None)
        content = responses[0]["content"]
        try:
            j_object = json.loads(content)
            return float(j_object["score"]) > self.threshold
        except json.JSONDecodeError:
            return False


class EInvoiceAgent:
    def __init__(
        self, short_memory: ShortTermMemory, vector_memory: ChromaMemory, config: dict
    ):
        self.short_memory = short_memory
        self.vector_memory = vector_memory

        core_config = config.get("core", None)
        pre_filter_config = config.get("pre-filter", None)
        post_filter_config = config.get("post-filter", None)
        for cfg in [core_config, pre_filter_config, post_filter_config]:
            assert cfg is not None

        self.core_llm = Text_to_Text(
            connection_string=core_config.get("connection_string"),
            system_prompt=core_config.get("system_prompt"),
            config=core_config.get("config"),
            tools=core_config.get("tools", None),
        )
        self.pre_filter_llm = RelevancyFilter(
            core=Text_to_Text(
                connection_string=pre_filter_config.get("connection_string"),
                system_prompt=pre_filter_config.get(
                    "system_prompt", RELEVANCY_FILTER_PROMPT
                ),
                config=pre_filter_config.get("config"),
                tools=None,
            ),
            threshold=pre_filter_config.get("threshold", 0.5),
        )
        self.dream_catcher = DreamCatcher(
            core=Text_to_Text(
                connection_string=post_filter_config.get("connection_string"),
                system_prompt=post_filter_config.get(
                    "system_prompt", DREAM_CATCHER_PROMPT
                ),
                config=post_filter_config.get("config"),
                tools=None,
            ),
            threshold=pre_filter_config.get("threshold", 0.5),
        )

    def prepare_context(self, query: str) -> list[dict]:
        # Prepare Context
        context: list[dict] = []
        # Retrieve Recent Interaction
        sml = len(self.short_memory.to_list())
        if sml > 0:
            last_n = self.short_memory.last_n(min(sml, 5))
            context.extend(last_n)
        self.short_memory.push({"role": "user", "content": query})
        # Retrieve Relevant Documents
        resp = self.vector_memory.query(query_string=query, return_n=20)
        vmq_result = resp["result"]
        docs = vmq_result["document"]
        for doc in docs:
            context.append({"role": "user", "content": doc})

        return context

    def ask(self, query: str) -> list[dict]:
        # Prepare Context
        context = self.prepare_context(query)

        # Pre-Generation Filter
        context = self.pre_filter_llm.select_relevant(query, context)
        context_len = len(context)

        # LLM Generation
        llm_generated_responses = self.core_llm.run(
            query=query, context=context if context_len > 0 else None
        )

        # Post-Generation Filter
        if self.dream_catcher.catch(llm_generated_responses, context):
            for response in llm_generated_responses:
                self.short_memory.push(response)
            return llm_generated_responses
        return [
            {
                "role": "assistant",
                "content": "I don't want to lie, I don't know the answer to your question.",
            }
        ]
