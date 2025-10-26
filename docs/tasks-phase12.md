## 🗂️ TASKS.md

### **Phase 1.1 – Project Initialization & Core Setup**

> **Goal:** Establish the technical foundation for both backend and frontend systems.

[x] Set up project structure, Docker Compose, PostgreSQL, Neo4j, and environment configuration
[x] Initialize FastAPI backend with project structure, dependencies, and configuration
[x] Initialize Next.js 15 frontend with shadcn/ui, Tailwind CSS, and project structure
[x] Implement authentication system with NextAuth and FastAPI JWT endpoints
[x] Build document upload functionality (backend API + frontend UI with drag-and-drop)
[x] Implement .md document parsing

---

### **Phase 1.2 – Knowledge Graph & Basic Q&A**

> **Goal:** Build the fundamental GraphRAG pipeline and enable basic question-answering capabilities.

[ ] Integrate gemini-2.5-flash-lite for entity and relationship extraction
[ ] Build Neo4j graph service to create and populate the knowledge graph
[ ] Implement basic Q&A with simple graph retrieval and answer generation
[ ] Create a basic testing dashboard and verify Phase 1 functionality

---

### **Phase 2 – Advanced Graph Intelligence & Optimization**

> **Goal:** Enhance system intelligence, multi-level retrieval, and performance optimization.

[ ] Implement community detection using Neo4j GDS library
[ ] Generate and store community summaries using Gemini
[ ] Build multi-level retrieval with hierarchical search strategy
[ ] Improve entity extraction with better prompts and refinement loops
[ ] Enhance Q&A system with community-based retrieval and multi-perspective answers
[ ] Create graph visualization tools for debugging and query path display
[ ] Implement Redis caching, database optimization, and performance improvements
