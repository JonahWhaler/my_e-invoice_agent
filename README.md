# Prerequisite
- **Ollama**: This is needed to use models through Ollama.
  - [Download](https://ollama.com/)
  - Remember to pull models you need with `ollama pull <model_name>:<tag>`
- **OpenAI API Key**: This is needed to use OpenAI's API.
  - [Apply API Key](https://platform.openai.com/docs/quickstart)
- **llm-agent-toolkit**: This is the Python package we will be using.
  - `pip install llm-agent-toolkit`
- **FFmpeg**: This is needed to handle audio files.
  - [Download FFmpeg](https://www.ffmpeg.org/download.html).

# Diagrams
## Build Knowledge Base
![Build Knowledge Base](https://github.com/JonahWhaler/my_e-invoice_agent/blob/main/diagram/diagram-Build%20Knowledge%20Base.png)

## Overview
![Overview](https://github.com/JonahWhaler/my_e-invoice_agent/blob/main/diagram/diagram-Zoom%20Out.png)

# agents.py
Find the implementation of agents here. In summary, the agent has long short-term memory with three individual Text_to_Text LLM Core to handle perigenerative activities (Pre-generation, Intra-generation, and Post-generation).

# tools.py
Find the implementation of tools here.

# Cookboo 1.ipynb
Find the complete configuration and execution order here.
