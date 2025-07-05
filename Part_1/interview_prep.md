# Part 1 – Form Extraction System

## 1. Business Purpose
The web-app lets a clerk/doctor upload an Israeli National-Insurance (ביטוח לאומי) injury form and instantly receive a structured JSON payload. This payload can be pushed downstream to EMR or analytics – eliminating manual data entry.

## 2. Architecture at a Glance

## 4. Configuration & Secrets
File `Core/config.py` loads `.env` via `python-dotenv`:
```
AZURE_DOC_INT_KEY
AZURE_DOC_INT_ENDPOINT
AZURE_OPENAI_KEY
AZURE_OPENAI_VERSION
AZURE_OPENAI_ENDPOINT
```
Model deployments hard-coded: `gpt-4o` and `gpt-4o-mini`.

## 5. Dependencies (Why Each Exists)
| Package | Reason |
|---------|--------|
| streamlit | Rapid UI + file upload |
| pandas | Tabular metrics & display |
| Pillow | Image-type detection in UI |
| python-dotenv | Load secrets locally |
| openai | Call Azure OpenAI |
| azure-ai-documentintelligence | Call DI OCR API |

## 5-bis. Detailed Tools, Libraries & Concepts
The **table above is the quick view**; the list below explains _why_ every item matters and **where it is referenced in code**.

### Cloud Services
1. **Azure Document Intelligence** – SaaS OCR able to handle Hebrew bidirectional text. Wrapped by `Service/ocr.py` (`DocumentIntelligenceClient`).
2. **Azure OpenAI** – GPT-4o & GPT-4o-mini chat plus `text-embedding-ada-002` embeddings. Used by `Service/extractor.py` and (indirectly) the validator for future accuracy checks.

### Python Libraries / SDKs
| Library | Purpose | Key Files |
|---------|---------|-----------|
| `streamlit` | File-upload UI, tabbed results display | `app.py` (all UI elements) |
| `azure-ai-documentintelligence` | Call DI OCR REST | `Service/ocr.py` |
| `openai` | Azure OpenAI chat completions | `Service/extractor.py` |
| `pandas` | Build tabular metrics dataframe for display | `app.py` (metrics tab) |
| `Pillow` | Detect image type & render previews | `app.py` (image handling) |
| `python-dotenv` | Load `.env` into `os.environ` | `Core/config.py` |
| `pydantic` | Data model (`Core/schema.py::Form`) ensures typed output | `Service/extractor.clean()` |
| `logging` | Uniform log format, UTF-8 for Hebrew | `Core/log_config.py`, `app.py` |

### Architectural / Coding Concepts
| Concept | Why it matters | Implementation |
|---------|----------------|-----------------|
| **OCR pre-processing vs. post-processing** | Keep raw OCR JSON but also flatten into full_text & lines for later ML / audit | `Service/ocr.process()` |
| **Prompt Engineering** | Two-prompt strategy isolates system rules from user text | `Service/extractor.system_prompt()` + `.extraction_prompt()` |
| **JSON mode** | Guarantees parser-friendly output; reduces validation errors | `Extractor.extract_fields(response_format={...})` |
| **Data Cleaning** | Normalises phone/ID/date keys regardless of GPT variations | `Extractor.clean()` |
| **Validation Layer** | Separate business rules from extraction; easy to swap rules | `Service/validator.py` |
| **Environment Isolation** | Using a thin `requirements.txt` speeds CI & avoids C-extensions | curated file |
| **Streamlit `@st.cache_resource`** | Ensures single OCR/OpenAI client per worker → cost & perf | `services()` in `app.py` |
| **Mermaid Diagrams** | Included in this prep doc for quick architecture recall | Section 2 above |

> Tip: be ready to reference the **exact file & function names** when asked _"Where do we call Azure OpenAI?"_.

## 6. Logging Strategy
`logging.basicConfig` in `app.py` prints to console; OCR & Extractor use `Core/log_config.py` → rotating INFO/ERROR files under `Part_1/Log` (same formatter reused in Part 2).

## 7. Failure Points & Mitigation
| Risk | Handling |
|------|----------|
| Bad env vars | Raises at service init, caught in `process()` and displayed via `st.error()` |
| GPT returns non-JSON | `JSONDecodeError` caught; retry logic placeholder via `retry_count` |
| Low OCR confidence | Validator surfaces via low completeness/confidence scores |
| Large files | Model limit 20 pages documented in README |

## 8. Demo Script
```bash
# assume venv active & env vars set
pip install -r Part_1/requirements.txt
streamlit run Part_1/app.py  # open http://localhost:8501
```
Upload `Data/phase1_data/sample.pdf` → walk through tabs.

## 9. Possible Extension Questions
* Batch processing via Queue / Azure Functions?
* Persist JSON to Cosmos DB?
* Internationalisation beyond Hebrew/English?

## 10. Interview Cheat-Sheet – 10 Q&A
| # | Question | Answer Sketch |
|---|----------|---------------|
|1|Why Azure DI over Tesseract? | DI gives Hebrew OCR, layout, tables + SaaS reliability.|
|2|How do you ensure JSON validity from GPT? | `response_format` + `max_tokens` + `json.loads` with explicit failure branch.|
|3|Why store full text & lines separately? | Lines enable bounding-box display / manual review; full text feeds GPT.|
|4|What's the ID validation rule? | Regex `^\\d{9}$` and optional Luhn-style checksum extension.|
|5|Explain completeness score. | filled / total fields; required fields weight missing heavily.|
|6|How do you calculate confidence per section? | Currently heuristic: present-vs-missing, can plug DI confidences.|
|7|Concurrency in Streamlit? | Each user gets a separate session but `@st.cache_resource` ensures single service instances per worker.|
|8|How would you speed up extraction? | Async OCR calls, GPT parallel on page chunks, caching embeddings.|
|9|What are API cost controls? | Confidence threshold, max_retries, request batching.|
|10|Prod hardening steps? | Auth, HTTPS, retry/back-off, Sentry, CI tests, IaC.

## 11. Walkthrough Progress & Next Steps

### What We Have Covered So Far
- **app.py**: Full walkthrough of the Streamlit UI, pipeline orchestration, session state, and resource caching.
- **Logging**: Upgraded to robust, production-ready logging with rotation, alignment, and log directory under Part_1/Log.
- **Streamlit Concepts**: Explained `st.session_state`, `st.cache_resource`, and singleton pattern for services.
- **Schema**: Deep dive into `Core/schema.py` (Pydantic models, validation, field aliases, config, and output method).
- **Config**: Reviewed `Core/config.py` (environment variable loading, API keys, and settings).
- **OCR**: Walked through `Service/ocr.py` (Azure Document Intelligence integration, result processing).
- **Extractor**: Walked through `Service/extractor.py` (prompt engineering, OpenAI API calls, cleaning).
- **Validator**: Walked through `Service/validator.py` (business rules, completeness, section metrics, reporting).
- **requirements.txt**: Discussed dependency rationale and customizations.
- **Project Structure**: Clarified the role of `__pycache__` and directory layout.

### Next Steps to Complete
- Walk through validator and actual PDF fields in depth
- Retry the system
- Add pics of code to README file

Let me know which you want to tackle next!