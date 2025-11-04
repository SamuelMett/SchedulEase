# SchedulEase

## Phase 1: Project Concept, User Research & AI Model Exploration

### Weight: 15% of final grade

#### Objective

Students will form teams (2-3 members) and develop a comprehensive project concept that
combines user needs with AI capabilities. This phase emphasizes understanding both your users
and the AI tools available to serve them.
Key Deliverables

### 1. Project Proposal (25% of phase grade)

#### Requirements

- Problem Statement: Clearly define the problem your application will solve
  - A file upload webapp that can scan uploaded files metadata and schedule events on a google calendar while saving a file summary.
- Target Users: Identify your primary and secondary user groups
  - Primary: Students
  - Secondary: Business managers/supervisors
- Core Functionality: Outline 5-7 key features your application will provide
  - Upload a pdf, csv, json, etc. file
  - Read the files metadata, scanning text
  - Google calendar integration to automatically schedule events
  - Intuitive AI that can summarize and automatically schedule events accurately and rating criticality
  - Webapp capable of high availability, confidentiality, and integrity
  - Interactive UI that is easy to use
- AI Integration Strategy: Explain how AI will enhance the user experience (not just add complexity)
  - AI will be used in the backend to scan files, decipher dates, and use the google api to schedule events like tests and homework due
- Success Metrics: Define how you'll measure if your solution works
  - The success rate of recognizing critical events such as exams and if it schedules them at the right day.
  - Exact time of the day the event is
  - Homework is classified correctly by level of importance
  - Summaries are accurate and are added to description/details of event

### 2. AI Model Research & Selection (35% of phase grade)

#### Requirements 2

- Model Exploration: Research and evaluate at least 5 pre-trained models that could
enhance your application
- Technical Assessment: For each model, document:
  - Input/output requirements
    - Take in a pdf, txt, etc file
    - Summarizes documents
    - Extracts accurate times and dates
    - Automatically schedule events in Google Calendar
    - Chatbot to help with manually scheduling events or fixing errors
    - Confirmation of event before scheduling
  - API limitations and rate limits
    - Unlimited rates (local)
    - Processing power limitation (Macbook Air M2)
    - Not as smart as an 8b model
  - Response time expectations
    - between 30 seconds and 2 minutes for any feature
  - Cost considerations (if applicable)
    - 0$ so far
- Final Model Selection: Choose 1-2 models and justify your selection based on user needs and technical feasibility
  - Gemma3:4b Ollama
- Integration Plan: Outline how these models will work within your user flow
  - The plan is for the 4b model to handle everything assuming it is smart enough to do these things correctly most of the time. With testing the model, we found it extracts dates in the correct format, summarizes great, and is fast with the M2 Macbook

### 3. User Research & Personas (40% of phase grade)

#### Requirements 3

- User Interviews: Conduct interviews with at least 6 potential users
- Research Synthesis: Identify key user needs, pain points, and goals
- Persona Development: Create 3 detailed user personas including:
  - Demographics and background
  - Goals and motivations
  - Pain points and frustrations
  - Technology comfort level
  - Relationship with AI/automation
  - Context of use scenarios

#### AI-Specific Considerations

- How do users currently solve the problem your AI will address?
  - Manually schedule these dates such as class schedules by hand for a single 4 month semester.
  - Having to look through syllabuses to schedule important exam dates
  - Reading a long document with a ton of copied or unnecessary information
- What are their expectations and concerns about AI-powered solutions?
  - It will take their jobs
  - It will rise up and turn evil
  - It will schedule events wrong
- What level of AI transparency do they need?
  - How the information is being used (if being stolen/trained)
