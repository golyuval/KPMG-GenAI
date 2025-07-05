## Interview Checklist

### Project Flow
- [ ] Can you outline the end-to-end flow of data and processes in the project?
- [ ] What are the key decision points or branches in the workflow?
- [ ] How does each component interact with upstream and downstream modules?

### Project Faults
- [ ] What are the most common sources of errors or failures in the system?
- [ ] How do you detect, log, and respond to faults in production?
- [ ] What strategies are in place for fault tolerance and recovery?

### Project Replacements
- [ ] Which parts of the system are designed to be easily replaceable or upgradable?
- [ ] What criteria do you use to evaluate and select replacement components?
- [ ] Can you describe a scenario where you had to swap out a major module? What was the impact?

### AI Models (Deep Understanding & Selection)
- [ ] What are the most prominent AI models available today, and what are their core strengths and weaknesses?  
  - **OpenAI:** GPT‑4.1, GPT‑4.1 mini, GPT‑4o  
  - **Anthropic:** Claude Opus 4, Claude Sonnet 4  
  - **Google (DeepMind):** Gemini 2.5 Pro, Gemini 2.5 Flash  
  - **Meta:** Llama 4 Scout, Llama 4 Maverick  
  - **Mistral:** Mistral Medium 3, Mistral Small 3.1  
  - **Alibaba:** Qwen 3, Qwen 2.5 Max  
  - **Baidu:** ERNIE 4.5  
  - **DeepSeek:** DeepSeek‑V2, DeepSeek‑Coder  
- [ ] For which use cases or scenarios would you choose each model, and why? (Consider reasoning, creativity, compliance, speed, context window, multimodality, open-source, etc.)
- [ ] How do you compare and evaluate models for your needs (benchmarks, licensing, integration, cost, ecosystem)?

### AI Updates (Industry-Wide)
- [ ] What are the most significant recent updates in the AI industry (e.g., new model releases, breakthroughs in context window, multimodal capabilities, agent frameworks, open-source trends)?
- [ ] How do these updates impact the broader AI landscape and potential applications?
- [ ] Which updates do you consider most relevant for future adoption or experimentation?

### RAG Field (Progress & Tools)
- [ ] What are the latest advancements in Retrieval-Augmented Generation (RAG), including new architectures, evaluation methods, and scaling techniques?
- [ ] Which tools and frameworks are most widely used for RAG today (e.g., Langchain, LlamaIndex, Haystack, OpenAI RAG, Gemini RAG, Cohere RAG, etc.), and what are their comparative strengths?
- [ ] How do you assess the effectiveness, flexibility, and integration capabilities of different RAG solutions?

### Training Approaches (Progress & Tools)
- [ ] What are the current state-of-the-art training approaches for LLMs and AI systems ?
- [ ] What new tools, platforms, or automation solutions have emerged for model training, evaluation, and deployment (e.g., MosaicML, Hugging Face, vLLM, SkyPilot, Colossal-AI)?
- [ ] How do you compare the effectiveness, scalability, and cost of different training strategies?

### Langchain Advancements & Competitors
- [ ] What are the most important recent advancements in Langchain (modules, integrations, agent frameworks, RAG support, etc.)?
- [ ] What are the main competitors to Langchain on the web (e.g., LlamaIndex, Haystack, OpenAI's native tools, Dust, Flowise, CrewAI, AutoGen, Semantic Kernel, etc.), and how do they compare in terms of features, flexibility, and adoption?
- [ ] How do you decide which orchestration or agent framework to use for a given project, and what are the trade-offs?

## Part 1 Changes
- Changed the logger in Part_1/app.py to use get_module_logger from Core.log_config instead of logging.basicConfig.

---




