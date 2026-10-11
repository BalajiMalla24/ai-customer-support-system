# **End Semester Project Report Guidelines: Agentic AI Systems**

**1. Title Page** The first page should contain the project title,
project domain, student name(s), roll number(s), course name, instructor
name, and date of submission.

**2. Abstract** Provide a brief summary of the project in about 150--200
words. This should include the objective of the study, the agentic
approach followed, the specific models used (including local/offline
models), and the key findings or outcomes.

**3. Problem Definition & Domain** Clearly describe the objective of the
project. Identify the chosen domain (e.g., Academic Research Detective,
Hyper-Local Smart City Navigator, Cyber-Defense Triage) and explain the
complex real-world challenge it addresses. Explain why this specific
problem benefits from autonomous reasoning, planning, and tool usage.

**4. System Architecture & Agent Roles** Describe the overall hybrid AI
architecture of your system, combining cloud and local intelligence.
List and describe the multiple agents or components involved. Explicitly
define which agent acts as a planner, which executes tasks, and which
retrieves information. Identify which agent(s) operate using an offline
or locally hosted model.

**5. Memory Integration & Knowledge Retrieval (RAG)** Explain the
Retrieval-Augmented Generation (RAG) setup used to incorporate external
knowledge retrieval (documents, APIs, logs, or databases) to improve
reasoning. Describe how agents maintain contextual memory, such as
conversation history, task state, or historical data. Detail the use of
any vector databases or structured memory stores used.

**6. Tool Usage & Environment Setup** List the specific tools your
agents interact with to complete tasks. Explain how the agents interface
with external APIs, databases, search engines, or data processing
modules. Provide examples of the inputs and outputs expected when agents
trigger these tools.

**7. Agent Planning & Orchestration**

-   **7.1 Planning Mechanism:** Detail the planning mechanism where an
    > agent decomposes a complex goal into smaller tasks.

-   **7.2 Execution Workflow:** Describe how these smaller tasks are
    > executed sequentially by the agents.

-   7.3 Agent Coordination: Explain the workflow and how multiple agents
    > or components coordinate tasks through structured workflows.

### 8. Validation and Testing of Agentic Systems

-   **Unit Testing for Tools:** Describe how individual tools (APIs,
    > database queries, or search functions) were validated to ensure
    > they return the expected data formats before being handed to an
    > agent.

-   **Trajectory Analysis:** Provide a \"trace\" or step-by-step log of
    > a complex task. Show how the agent moved from reasoning to
    > planning, and finally to execution.

-   **Consistency Testing:** Since LLMs can be non-deterministic,
    > describe how many times you ran the same high-level prompt and
    > whether the agent reached the same conclusion or followed a
    > similar path.

-   **Robustness & Error Handling:** Explain how the system handles
    > \"tool failure\" (e.g., an API is down or a search returns no
    > results). Does the agent retry, change its plan, or inform the
    > user?.

-   **Evaluation Metrics for RAG:** If using Retrieval-Augmented
    > Generation, specify the metrics used to validate the relevance of
    > retrieved documents (e.g., Faithfulness or Answer Relevance).

-   **Human-in-the-Loop (Optional):** If applicable, describe any points
    > where a human validates the agent's plan before it executes a
    > critical tool or action.

**9. System Evaluation** Present how the system\'s performance was
evaluated. Compare the performance of all models utilized in the system,
specifically noting how offline/local models handled tasks compared to
cloud models.

**10. Results and Insights** Discuss the key findings from the agentic
system\'s execution. Highlight how well the system improved its
reasoning and decision-making through RAG and external knowledge
retrieval. Provide meaningful interpretations relevant to the problem
domain.

**11. Conclusion** Summarize the overall work carried out. Mention the
most effective agent configuration and its overall performance. Provide
a brief statement on the main takeaway from the project.

**12. Limitations** Mention any limitations related to model context
windows, tool integration failures, local model latency, or assumptions
made during the project.

**13. Future Work** Suggest possible improvements such as using more
data, integrating advanced models, or extending the project further.

**14. References** List the external knowledge sources, tools,
libraries, or external references used.

**General Instructions for Report Preparation**

-   The report should be clear, structured, and concise.

-   Avoid including unnecessary code; focus on explanation and
    > interpretation.

-   All figures and tables should be properly labeled.

-   The report length should typically be between 15 and 20 pages.

-   Emphasis should be on understanding, analysis, and insights rather
    > than only model accuracy.
