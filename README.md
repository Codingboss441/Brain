# Brain

Intelligent Insurance Ticket Automation System
1. Overview
This project is a sophisticated, AI-powered automation system designed to streamline and enhance the processing of support tickets from Freshdesk, specifically tailored for insurance brokerage operations.

The system intelligently analyzes Freshdesk tickets by understanding their content, classifying attachments, deciphering complex parent-child ticket relationships, and determining the current workflow status. It leverages AI models from Anthropic (Claude) and a dedicated internal Document Reader API to perform Root Cause Analysis (RCA), generate context-aware responses, and suggest autonomous actions based on a comprehensive internal knowledge base of Standard Operating Procedures (SOPs).

The primary goal is to reduce manual effort, improve response times, ensure procedural consistency, and provide actionable insights to support agents.

2. Key Features
Automated Ticket Triage & Classification: Ingests Freshdesk tickets and classifies them into precise categories (e.g., Claims-Motor, Endorsement-Health-Financial, Support-PDPNR) using an extensive SOP-based rule engine.

Intelligent Document Analysis (OCR):

Processes various document formats including images (JPG, PNG) and PDFs.

Utilizes a dedicated Image Reader API for high-accuracy Optical Character Recognition (OCR) and structured data extraction (e.g., Aadhaar, PAN, Policy Numbers).

Classifies a wide range of insurance-related documents, such as RC Book, Policy Document, Claim Form, and more.

Analyzes document quality and provides actionable recommendations.

Contextual Ticket Understanding:

Analyzes the full conversation history to understand the ticket's lifecycle.

Deciphers complex parent-child ticket relationships, consolidating information for a holistic view.

Accurately determines the current "pending from" status (e.g., Customer, Insurer, Dealer) with a confidence score, going beyond simple ticket status fields.

SOP-Driven Workflow Automation:

Document Requirement Engine: Dynamically determines the list of required and optional documents based on the claim type and specific insurer.

Autonomous Action System: Suggests and can execute next-step actions like sending reminders, escalating tickets, or requesting documents, strictly following pre-defined SOPs.

Workflow Engine: Manages multi-step processes for claims and endorsements, tracking progress and deadlines.

AI-Powered Insights:

Root Cause Analysis (RCA): Uses Anthropic Claude to summarize complex ticket histories into a concise "Problem, Why, Solution" format.

Predictive Analytics: Forecasts key metrics like escalation risk, estimated resolution time, and customer satisfaction risk.

Smart Response Generation: Crafts accurate, context-aware, and non-hallucinatory email responses grounded in the verified facts of the ticket.

Data Persistence: Caches processed ticket summaries in an Excel file to prevent redundant analysis and provide quick lookups.

3. Architecture & Workflow
The system follows a modular, pipeline-based approach for processing each ticket:

Ticket Ingestion: Fetches a ticket and its full conversation history from the Freshdesk API.

Content & Document Analysis:

Attachments are processed in parallel by the DocumentAnalyzer via the Image Reader API to classify them and extract data.

The entire text content is consolidated for NLP analysis.

Classification & SOP Mapping: The ticket content is classified using the classify_ticket_with_sop function, which maps the ticket to a specific internal process and its corresponding SOP.

Contextual Analysis: The EnhancedTicketAnalyzer deciphers parent-child relationships, determines the true "pending from" status, and builds a complete timeline of the ticket's journey.

AI-Powered Summary & Insights:

Anthropic Claude generates a "Problem, Why, Solution" summary.

The PredictiveAnalyticsEngine forecasts potential outcomes.

The AutonomousActionSystem suggests SOP-aligned actions.

Response Generation: If required, the SmartResponseGenerator crafts a draft response that is fact-checked against the ticket's content to prevent AI hallucination.

Data Caching: The final summary and analysis are saved to ticket_summary.xlsx.

4. Core Components
DocumentAnalyzer: Handles all document-related tasks, including OCR and classification using the Image Reader API.

EnhancedTicketAnalyzer / EnhancedContextualRoutingAnalyzer: The brain of the system for understanding the ticket's state, relationships, and history.

DocumentRequirementEngine: A rule-based module that acts as a knowledge base for insurer-specific document needs.

SmartResponseGenerator: A sophisticated prompt-engineered module to generate safe and accurate AI replies.

AutonomousActionSystem: Orchestrates SOP-based actions, from sending alerts to escalating tickets.

classify_ticket_with_sop(): The core function that maps a ticket's content to a structured internal process.
