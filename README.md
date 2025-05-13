### 🌍 Stateless. Scalable. Multi-LLM.

# **The Next Evolution in AI Agent Orchestration (AI Agent Core Engine)**

Run and scale intelligent agents across **multiple LLMs** — without managing state or sessions.
Built on the **SilvaEngine serverless framework**, our platform delivers **rolling context memory**, modular **function calling**, and real-time **conversation monitoring** — all in one unified, AI-native control plane.

**⚡ Stateless by design** – infinite scale, instant recovery

**🧠 Model-agnostic** – OpenAI, Anthropic, Gemini, and more

**🔌 Modular architecture** – plug-and-play function routing

**📈 Fully observable** – every conversation, recorded and traceable

## **Introduction**

🌐 **The World’s First Stateless Multi-LLM Agent Orchestration Platform**

Welcome to the future of AI agent infrastructure — a revolutionary platform that redefines how intelligent agents are deployed, scaled, and orchestrated across diverse LLM ecosystems. Powered by the **SilvaEngine serverless framework**, this stateless platform offers unmatched agility, reliability, and speed in handling AI-driven conversations at scale.

🔁 **Stateless by Design. Context-Rich by Architecture.**
Say goodbye to complex session management. Our platform enables **rolling context memory**, ensuring every conversation retains critical relevance — without the weight of persistent storage. This lets you scale infinitely, recover instantly, and run lightweight AI agents that remain deeply aware and responsive.

🧠 **Multi-Model Intelligence. Modular Functionality.**
Orchestrate and switch between top-tier LLMs — OpenAI, Anthropic, Gemini, and more — in real time. Our modular function-calling engine enables **plug-and-play capabilities**, allowing agents to invoke domain-specific tools and workflows, no matter which model powers the response.

🔍 **Thread-Aware Monitoring & Observability**
Every conversation is **recorded, versioned, and monitored**, giving your teams full visibility into interaction history, decision logic, and user intent. Gain insights, audit compliance, and optimize performance with intelligent observability built into the core.

🧩 **Built for Builders. Trusted by Enterprises.**
Whether you're launching autonomous agents, enhancing customer service, or powering next-gen copilots, this platform equips you with the **flexibility of serverless**, the **power of orchestration**, and the **precision of stateless memory** — all in one unified, AI-native control plane.

🔐 **Secure. Scalable. Future-Proof.**
Designed to meet the needs of mission-critical applications, our platform embraces security-first principles, auto-scaling infrastructure, and modular integration to support evolving enterprise demands in AI deployment.

### Key Features

#### 🔧 **Core Features**

| **Feature**                            | **Description**                                                              |
| -------------------------------------- | ---------------------------------------------------------------------------- |
| **Stateless Architecture**             | Eliminates session handling for infinite scalability and instant recovery.   |
| **Rolling Context Memory**             | Maintains conversational context without persisting full session state.      |
| **Multi-LLM Orchestration**            | Real-time switching and integration across OpenAI, Anthropic, Gemini, etc.   |
| **Modular Function Calling**           | Plug-and-play routing of tool/function calls across different models.        |
| **Serverless Framework (SilvaEngine)** | Built on a scalable, lightweight, cloud-native infrastructure.               |
| **Model-Agnostic Compatibility**       | Supports diverse LLM providers with seamless fallback or parallel execution. |

---

#### 🧠 **Intelligence & Functionality**

| **Feature**                              | **Description**                                                                |
| ---------------------------------------- | ------------------------------------------------------------------------------ |
| **Thread-Aware Conversation Monitoring** | Tracks and logs conversations with full visibility and lineage.                |
| **Real-Time Decision Traceability**      | Each agent interaction is versioned and auditable for debugging or compliance. |
| **Autonomous Agent Enablement**          | Designed to support agent autonomy with dynamic decision-making.               |
| **Domain-Specific Tool Invocation**      | Agents can call tools dynamically based on domain and user context.            |

---

#### 📊 **Observability & Control**

| **Feature**                      | **Description**                                                     |
| -------------------------------- | ------------------------------------------------------------------- |
| **Full Interaction Logging**     | Stores every user-agent exchange for analytics and optimization.    |
| **Versioned Execution Contexts** | Enables replay and regression testing of agent decisions.           |
| **Live Conversation Monitoring** | Allows real-time viewing and intervention of ongoing agent threads. |

---

#### 🔐 **Enterprise-Grade Infrastructure**

| **Feature**                    | **Description**                                                            |
| ------------------------------ | -------------------------------------------------------------------------- |
| **Security-First Design**      | Includes audit trails, identity boundaries, and secure execution policies. |
| **Auto-Scaling**               | Grows with usage demand without manual provisioning.                       |
| **Modular Integration Layer**  | Easily connects to internal tools, APIs, or databases.                     |
| **Future-Proof Compatibility** | Adapts to evolving AI models and enterprise infrastructure needs.          |


### 🧠 **Stateless Multi-LLM AI Agent Core Engine — Architecture Overview**
![AI Agent Core Engine Architecture Diagram](/images/ai_agent_core_engine_architecture.jpg)

This diagram showcases a **serverless, multi-LLM AI agent orchestration system** powered by **SilvaEngine**. It supports **real-time interactions over WebSocket**, integrates **multiple LLMs (OpenAI, Gemini, Claude)**, and executes tasks using **asynchronous Lambda functions and modular handlers**.

---

#### 🔄 **End-to-End Flow Description (Updated)**

##### 1. **User Interaction (WebSocket Query)**

* The **User** initiates a query via **WebSocket (WSS)**.
* The query is routed through **Amazon API Gateway**, acting as a real-time interface for bidirectional communication.

##### 2. **Initial Message Routing**

* API Gateway forwards the request to an **AWS Lambda** (`SilvaEngine Area Resource`) for validation, routing logic, and enqueueing.
* The message is pushed to **Amazon SQS** (`SilvaEngineTask Queue`) for asynchronous, decoupled task execution.

##### 3. **Agent Task Execution (Async)**

* **SilvaEngine Agent Task**, another Lambda function, dequeues the message and invokes:

  * Tool calling logic.
  * AI agent orchestration.
  * External function integrations.

##### 4. **AI Agent Core Orchestration**

* The **AI Agent Core Engine** acts as the **stateless orchestrator**. Responsibilities include:

  * Managing **conversation context** using **Amazon DynamoDB**.
  * Delegating the query to the appropriate **LLM Agent Handler** based on routing rules or model availability.

##### 5. **Multi-LLM Routing via Agent Handlers**

* The platform supports multiple language models via **dedicated handlers**:

  * **OpenAI Agent Handler** → routes to **OpenAI Response API**
  * **Gemini Agent Handler** → routes to **Google Gemini API**
  * **Anthropic Agent Handler** → routes to **Anthropic Claude API**

Each handler formats, sends, and processes responses independently, enabling **model-agnostic orchestration**.

##### 6. **Final AI Response Handling**

* The **AI Agent Handler** (green box) handles:

  * Response post-processing.
  * Tool call updates.
  * State updates and results formatting.
  * Sends **WebSocket replies** to the user via the original API Gateway connection.

---

#### 🌐 **New Capabilities Highlighted**

| Feature                    | Description                                                                         |
| -------------------------- | ----------------------------------------------------------------------------------- |
| **True Multi-LLM Support** | Unified engine dynamically selects and communicates with OpenAI, Gemini, or Claude. |
| **Modular Handler Layer**  | Handlers for each model can be independently managed, scaled, or extended.          |
| **Extensible Backend**     | Easily add future models or vendors by plugging in new handler modules.             |

---

### 🔄 **AI Agent Orchestration: Sequence Flow Description**
![AI Agent Core Engine Sequence Diagram](/images/ai_agent_core_engine_sequence_diagram.jpg)

#### 🧍‍♂️ **1. User Initiates Query**

* The **user** sends a query via WebSocket.
* The message is received by the system and triggers the **Resolve Ask Model** step.

---

#### 🔁 **2. Model Resolution & Execution Initiation**

| Step | Component                   | Description                                                                     |
| ---- | --------------------------- | ------------------------------------------------------------------------------- |
| ✅    | **Resolve Ask Model**       | Identifies which AI model (e.g., OpenAI, Gemini, Claude) to use.                |
| 🔄   | **Async Execute Ask Model** | Asynchronously invokes execution logic.                                         |
| 🚀   | **Execute Ask Model**       | Begins actual agent processing and prepares the message for the selected model. |

---

#### 🧠 **3. Language Model Interaction**

| Step | Component               | Description                                                                                         |
| ---- | ----------------------- | --------------------------------------------------------------------------------------------------- |
| 📩   | **OpenAIEventHandler**  | Handles communication with the OpenAI API.                                                          |
| 🤖   | **OpenAI Response API** | Processes the query and returns a structured response, potentially with function call instructions. |

---

#### 🔧 **4. Function Calling Workflow (if applicable)**

* If the response includes a **tool/function call**, it’s passed to the **Function Calling Module**.
* This module:

  * Executes the requested tool/module logic.
  * Triggers **multiple async updates** to the system about the tool's status:

    * 🔸 *Initial*
    * 🔸 *In Progress*
    * 🔸 *Completed*

---

#### 🔄 **5. Tool Call Handling and Agent Coordination**

| Component                         | Description                                                                                        |
| --------------------------------- | -------------------------------------------------------------------------------------------------- |
| **AI Agent Handler**              | Orchestrates the tool call update flow and prepares the final response.                            |
| **AWS SQS**                       | Used for decoupled communication and state update queuing.                                         |
| **Async Insert Update Tool Call** | Lambda functions or microservices that handle stepwise updates (initial → in progress → complete). |

---

#### 📤 **6. Final Delivery via WebSocket**

* Once the task is completed and results are ready:

  * The system asynchronously triggers **Send Data to WebSocket**.
  * The **user receives the final response** through the established WSS connection.

---

### 🧩 **Key Flow Highlights**

| Area                        | Purpose                                                                        |
| --------------------------- | ------------------------------------------------------------------------------ |
| ✅ Model Decoupling          | The LLM model execution is abstracted away from the user-facing logic.         |
| 🔄 Asynchronous Operations  | All tool updates and executions are handled via async invokes for scalability. |
| 🔌 Modular Function Calling | Allows LLM responses to dynamically trigger domain-specific operations.        |
| 📡 Real-time Delivery       | Results are delivered back to the user over the original WebSocket channel.    |

---

### 🧩 **ER Diagram Overview: Modular AI Agent Orchestration System**
![AI Agent Core Engine ER Diagram](/images/ai_agent_core_engine_er_diagram.jpg)

This ER diagram structures the system into the following core **logical domains**:

---

#### 🔵 **1. Language Models & Agent Definitions**

##### **`llms`**

* Stores metadata about each supported language model (OpenAI, Anthropic, Gemini, etc.).
* Keys: `llm_provider`, `llm_name`
* Includes: `module_name`, `class_name`, `updated_by`, `created_at`

##### **`agents`**

* Defines each AI agent version and its configuration.
* Keys: `endpoint_id`, `agent_version_uuid`, `agent_uuid`
* Maps to: `llm_provider`, `llm_name`
* Includes function mappings, tool call behavior, and message limits.

---

#### 🧠 **2. Thread & Message Management**

##### **`threads`**

* Represents a full conversation session (thread) for a user-agent pair.
* Keys: `endpoint_id`, `thread_uuid`
* Associates with: `agent_uuid`, `user_id`

##### **`messages`**

* Stores each individual message in a thread.
* Keys: `thread_uuid`, `message_uuid`, `run_uuid`
* Includes: `role`, `message`, `created_at`, etc.

##### **`runs`**

* Represents a single inference call in a conversation (mapped to a model request).
* Keys: `thread_uuid`, `run_uuid`
* Tracks: token usage, duration, endpoint\_id, etc.

---

#### ⚙️ **3. Tool Calling & Async Execution**

##### **`tool_calls`**

* Tracks all function/tool calls invoked by the agent within a thread and run.
* Keys: `thread_uuid`, `tool_call_uuid`, `run_uuid`
* Attributes: `tool_type`, `arguments`, `content`, `status`, `notes`, `time_spent`

##### **`async_tasks`**

* Logs background async operations such as tool executions or external API calls.
* Keys: `function_name`, `async_task_uuid`
* Includes: `endpoint_id`, `arguments`, `result`, `status`, `notes`, `time_spent`

---

#### 🧪 **4. Fine-Tuning Data Management**

##### **`fine_tuning_messages`**

* Stores structured messages and tool calls for supervised fine-tuning.
* Keys: `agent_uuid`, `message_uuid`, `thread_uuid`, `timestamp`
* Attributes: `role`, `tool_calls`, `weight`, `trained`

---

#### 🔄 **5. Modular Function Configuration**

##### **`functions`**

* Registry of callable functions used in tool calling.
* Key: `function_name`
* Includes: `function` object with `module_name`, `class_name`, and `configuration`.

##### **`configuration (OpenAI) as an example`**

* A nested structure defining configuration options specific to OpenAI integration as an example.
* Includes: `openai_api_key`, `tools`, `max_output_tokens`, `temperature`, etc.

---

### 🔗 **Entity Relationships Summary**

| Relationship                                | Description                                                   |
| ------------------------------------------- | ------------------------------------------------------------- |
| `agents ↔ llms`                             | Each agent maps to a specific LLM definition.                 |
| `threads ↔ agents`                          | A thread is linked to the agent version and endpoint.         |
| `messages ↔ threads`                        | Messages are grouped by thread and run.                       |
| `runs ↔ threads`                            | Each model inference (run) occurs in a thread context.        |
| `tool_calls ↔ runs/messages`                | Tool calls are tied to a specific run and message.            |
| `async_tasks ↔ tool_calls`                  | Background tasks are logged independently and asynchronously. |
| `fine_tuning_messages ↔ threads/tool_calls` | Enables training data extraction per thread.                  |

---

Certainly! Here's a rephrased and enhanced version:

---

## ⚙️**Deployment and Setup**

To successfully deploy and configure the AI Agent, please follow the detailed instructions provided in the [AI Agent Deployment Guide](https://github.com/ideabosque/ai_agent_deployment). This resource includes step-by-step guidance to ensure a smooth and efficient setup process.

## 🤖 **Agent Definition & Configuration (Event Handler Layer)**
![AI Agent Event Handler Class Diagram](/images/ai_agent_event_handler_class_diagram.jpg)

This section defines the architecture for how agents are implemented, extended, and executed using a modular, class-based event handling system. It enables **runtime polymorphism** across different language model providers such as OpenAI, Gemini, Anthropic, and Ollama.

---

### 🧩 **1. Base Class: `AIAgentEventHandler`**

The [`AIAgentEventHandler`](https://github.com/ideabosque/ai_agent_handler) serves as the **abstract base class** for all model-specific agent handlers. It defines the common interface and shared utilities required to run an agent against a target LLM.

#### **Core Attributes**

* `endpoint_id`: Identifier for the active agent.
* `agent_name`, `agent_description`: Metadata for logging and auditing.
* `short_term_memory`: Runtime memory or summarization store.
* `settings_dict`: Loaded model configuration.
* `accumulated_json`: Structured context/data accumulated across turns.

#### **Key Methods**

* `invoke_async_func(...)`: Dynamically invokes a registered Python function.
* `send_data_to_websocket(...)`: Streams output back to the user in real time.
* `get_function(...)`: Retrieve and load the target function to enable dynamic invocation during runtime, ensuring it's prepared and ready for execution as part of the function-calling workflow.
* `accumulate_partial_json(...)`: Handlers for structured data processing.

---

### 🧠 **2. Model-Specific Agent Handlers**

Each subclass provides a concrete implementation of `invoke_model()` for the designated provider.

---

#### ✅ **`OpenAIEventHandler`**

* **Client:** `openai.OpenAI`
* **Attributes:** `model_settings`
* **Method: `invoke_model(...)`**

  * Supports token tracking, function calling (`tool_calls`), and streaming.
  * Invokes OpenAI's Chat API using system/user messages.

Follow the detailed instructions for configration provided in the [OpenAI Agent Handler](https://github.com/ideabosque/openai_agent_handler)

---

#### 🌐 **`GeminiEventHandler`**

* **Client:** `genai.Client`
* **Attributes:** `model_settings`, `assistant_messages`
* **Method: `invoke_model(...)`**

  * Executes Gemini chat model with `prompt`, `tools`, and event streaming support.

Follow the detailed instructions for configration provided in the [Gemini Agent Handler](https://github.com/ideabosque/gemini_agent_handler)

---

#### 🧬 **`AnthropicEventHandler`**

* **Client:** `anthropic.Anthropic`
* **Attributes:** `model_settings`, `assistant_messages`
* **Method: `invoke_model(...)`**

  * Interacts with Claude via streaming or synchronous completions.
  * Handles threading and function return parsing.

Follow the detailed instructions for configration provided in the [Anthropic Agent Handler](https://github.com/ideabosque/anthropic_agent_handler)

---

#### 🧪 **`OllamaEventHandler`**

* **Client:** Embedded/local runtime (no external API)
* **Attributes:** `system_message`, `model_settings`, `tools`
* **Method: `invoke_model(...)`**

  * Integrates with locally hosted models via Ollama (e.g., LLaMA, Mistral).
  * Tool call handling supported through `tool_call`.

Follow the detailed instructions for configration provided in the [Ollama Agent Handler](https://github.com/ideabosque/ollama_agent_handler)

---

## 🔄 **Key Design Benefits**

| Feature                    | Description                                             |
| -------------------------- | ------------------------------------------------------- |
| **Pluggable Architecture** | Add support for any new LLM by implementing a subclass. |
| **Unified Runtime API**    | Standardized agent behavior across models.              |
| **Streaming & Async**      | Natively supports event streaming and async updates.    |
| **Tool Calling**           | Fully integrated function call support across models.   |


## **Testing and Prototype**