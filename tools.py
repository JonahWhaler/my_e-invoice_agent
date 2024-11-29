import asyncio
import json
from random import choice as random_choice
import requests  # type: ignore
import aiohttp
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup  # type: ignore

from llm_agent_toolkit import (
    FunctionParameters,
    FunctionProperty,
    FunctionPropertyType,
    Tool,
    FunctionInfo,
)  # type: ignore


class DDGSearch(Tool):
    def __init__(
        self, region: str, safe_search: str = "off", pause_second: float = 0.5
    ):
        fi = FunctionInfo(
            name="DuckDuckGoSearch",
            description="Search the web through DuckDuckGo",
            parameters=FunctionParameters(
                required=["query"],
                type="object",
                properties=[
                    FunctionProperty(
                        name="query",
                        type=FunctionPropertyType.STRING,
                        description="The query string",
                    ),
                    FunctionProperty(
                        name="top_n",
                        type=FunctionPropertyType.NUMBER,
                        description="Number of results",
                    ),
                ],
            ),
        )
        super().__init__(func_info=fi, is_coroutine_function=True)
        self.__region = region
        self.__safe_search = safe_search  # on, moderate, off
        self.__pause_second = pause_second

    @property
    def region(self) -> str:
        return self.__region

    @property
    def safe_search(self) -> str:
        return self.__safe_search

    @property
    def pause_second(self) -> float:
        return self.__pause_second

    def run(self, params: str) -> str:
        j_params = json.loads(params)
        valid_input, error_msg = self.validate(**j_params)
        if not valid_input and error_msg:
            return error_msg

        query = j_params.get("query")
        top_n = j_params.get("top_n", 20)
        top_search = []
        with DDGS() as ddgs:
            for r in ddgs.text(
                keywords=query,
                region=self.region,
                safesearch=self.safe_search,
                max_results=top_n,
            ):
                top_search.append(r)
        for result in top_search:
            try:
                http_response = requests.get(url=result["href"], timeout=2)
                http_response.raise_for_status()
                text_data = http_response.text
                soup = BeautifulSoup(text_data, "html.parser")
                html_body = soup.find("body")
                if html_body:
                    result["html"] = soup.find("body").text
                else:
                    result["html"] = (
                        "Webpage not available, either due to an error or due to lack of permissions to the site."
                    )
            except requests.HTTPError as http_error:
                result["html"] = (
                    f"Webpage not available as a result of HTTP Error: {http_error}"
                )
            except Exception:
                result["html"] = (
                    "Webpage not available, either due to an error or due to lack of permissions to the site."
                )
        web_search_result = "$$$$$$$".join([f"{json.dumps(r)}" for r in top_search])
        return web_search_result

    async def run_async(self, params: str) -> str:
        j_params = json.loads(params)
        valid_input, error_msg = self.validate(**j_params)
        if not valid_input and error_msg:
            return error_msg

        query = j_params.get("query")
        top_n = j_params.get("top_n", 20)
        top_search = []
        with DDGS() as ddgs:
            for r in ddgs.text(
                keywords=query,
                region=self.region,
                safesearch=self.safe_search,
                max_results=top_n,
            ):
                top_search.append(r)
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_data(session, r["href"]) for r in top_search]
            search_results = await asyncio.gather(*tasks)
            for r, sr in zip(top_search, search_results):
                r["html"] = sr
        web_search_result = "$$$$$$$".join([f"{json.dumps(r)}" for r in top_search])
        return web_search_result

    @property
    def random_user_agent(self) -> str:
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) Firefox/120.0",
        ]
        return random_choice(user_agents)

    @property
    def headers(self) -> dict:
        return {
            "User-Agent": self.random_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

    async def _fetch_data(self, session, url):
        try:
            await asyncio.sleep(self.pause_second)
            async with session.get(url, headers=self.headers) as response:
                data = await response.text()
                soup = BeautifulSoup(data, "html.parser")
                return soup.find("body").text
        except Exception as _:
            return "Webpage not available, either due to an error or due to lack of access permissions to the site."


if __name__ == "__main__":
    ddx = DDGSearch(region="my", safe_search="on", pause_second=0.1)

    PARAMS = {"query": "Malaysia e-Invoice SDK"}
    responses = asyncio.run(ddx.run_async(json.dumps(PARAMS)))
    with open("./ddx.md", "w", encoding="utf-8") as writer:
        writer.write(responses)
