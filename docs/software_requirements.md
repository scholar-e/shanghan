# Software Engineering Requirements - Shanghan-TCM Evidence v1

## 1. Project Overview

**Project Name:** Shanghan-TCM Evidence  
**Project Type:** AI-powered Clinical Decision Support & Learning Platform  
**Core Functionality:** Bilingual (Chinese/English) AI assistant for Traditional Chinese Medicine practitioners and students, based on the Shang Han Lun classical text.  

**Target Users:**
- Licensed TCM practitioners and acupuncturists
- Advanced TCM students
- Educators and instructors
- TCM researchers

---

## 2. User Roles

| Role | Description | Access Level |
|------|-------------|--------------|
| Guest | Unregistered or newly registered user | Basic public content only |
| Student | Verified student account | Learning features, limited queries |
| Practitioner | Licensed TCM professional | Full clinical decision support |
| Contributor | Approved expert user | Case submission + practitioner features |
| Admin | System administrator | Full platform management |

---

## 3. User Authentication & Account

**REQ-ACC-001:** Users can register with email and password  
**REQ-ACC-002:** Users can log in and log out  
**REQ-ACC-003:** Users can reset their password via email  
**REQ-ACC-004:** Users can select their preferred language (English or Chinese)  
**REQ-ACC-005:** Users can update their profile information  
**REQ-ACC-006:** Users can delete their account and request data export  

---

## 4. Conversational Clinical Support

This is the core feature of the platform - an AI assistant that helps practitioners analyze patient presentations and identify relevant classical formulas.

### 4.1 User Input

**REQ-CHAT-001:** Users can describe patient chief complaints in free-text  
**REQ-CHAT-002:** Users can describe tongue diagnosis (color, coating, shape)  
**REQ-CHAT-003:** Users can describe pulse characteristics  
**REQ-CHAT-004:** Users can describe relevant history (onset, triggers, constitution factors)  
**REQ-CHAT-005:** Users can input in Chinese or English  
**REQ-CHAT-006:** The system asks follow-up questions when key information is missing  

### 4.2 AI Reasoning Output

**REQ-CHAT-007:** The system provides 1-3 candidate formulas with explanations  
**REQ-CHAT-008:** Each suggestion includes pattern reasoning (why this formula fits)  
**REQ-CHAT-009:** Each suggestion references classical basis (clause connection) without exposing raw text  
**REQ-CHAT-010:** The system suggests further assessment questions the practitioner should consider  
**REQ-CHAT-011:** Responses are in the user's selected language (Chinese or English)  

### 4.3 Safety & Disclaimers

**REQ-CHAT-012:** Every response displays a clear disclaimer that this is for educational/professional support only  
**REQ-CHAT-013:** The system refuses to provide self-diagnosis guidance for laypersons  
**REQ-CHAT-014:** For high-risk contexts (pregnancy, pediatric, severe acute conditions), the system advises immediate in-person evaluation  
**REQ-CHAT-015:** When insufficient information is provided, the system states it cannot give reliable suggestions  
**REQ-CHAT-016:** The system refuses to provide guidance for red-flag symptoms requiring emergency care  

### 4.4 Conversation Management

**REQ-CHAT-017:** Users can view their conversation history  
**REQ-CHAT-018:** Users can start new conversations  
**REQ-CHAT-019:** The system maintains context within a conversation  

---

## 5. Learning & Teaching Features

### 5.1 Clause and Formula Exploration

**REQ-LEARN-001:** Users can search for formulas by name or keyword  
**REQ-LEARN-002:** Users can search for clauses by pattern or symptom  
**REQ-LEARN-003:** Each formula displays: composition, functions, indications, common modifications, cautions  
**REQ-LEARN-004:** Each formula is linked to relevant classical clauses  
**REQ-LEARN-005:** Users can view formula variations and modifications  
**REQ-LEARN-006:** All formula information is available in Chinese and English  

### 5.2 Study Mode

**REQ-LEARN-007:** Users can browse clauses sequentially (as organized in Shang Han Lun)  
**REQ-LEARN-008:** Users can study formulas by category (e.g., exterior-releasing, heat-clearing)  
**REQ-LEARN-009:** Users can test their knowledge with interactive study aids (future consideration)  

### 5.3 Teaching Support

**REQ-LEARN-010:** Educators can use the system during live instruction  
**REQ-LEARN-011:** The system supports bilingual display for classroom use  

---

## 6. Expert Case Contribution (v1 - Limited)

*Note: Full case contribution system is deferred to v2. v1 includes internal expert case management only.*

**REQ-CASE-001 (Admin):** Admins can view submitted cases  
**REQ-CASE-002 (Admin):** Admins can review and approve/reject cases  
**REQ-CASE-003 (Admin):** Admins can link approved cases to relevant clauses and formulas  

---

## 7. Administration

### 7.1 User Management

**REQ-ADMIN-001:** Admins can view list of registered users  
**REQ-ADMIN-002:** Admins can suspend or activate user accounts  
**REQ-ADMIN-003:** Admins can assign user roles  

### 7.2 Content Management

**REQ-ADMIN-010:** Admins can add and edit formula entries  
**REQ-ADMIN-011:** Admins can add and edit clause content  
**REQ-ADMIN-012:** Admins can manage the knowledge base  

### 7.3 Monitoring

**REQ-ADMIN-020:** Admins can view usage statistics (number of users, conversations)  
**REQ-ADMIN-021:** Admins can review system logs for debugging  

---

## 8. Access Tiers

### 8.1 Free Tier

- Basic TCM conceptual Q&A
- Limited formula/clause searches (rate-limited)
- Learning content access

### 8.2 Professional Tier

- Full clinical decision-support chat
- Unlimited queries
- Detailed formula reasoning
- Full learning features

### 8.3 Contributor Tier

- All Professional features
- Case submission capabilities

---

## 9. Safety, Privacy & Compliance

**REQ-SAFE-001:** No personally identifiable patient information is stored in user conversations  
**REQ-SAFE-002:** Clinical cases in the knowledge base are fully de-identified  
**REQ-SAFE-003:** Internal annotations and expert content are never exposed to end users  
**REQ-SAFE-004:** All user data can be exported upon request  
**REQ-SAFE-005:** Users can delete their account and associated data  
**REQ-SAFE-006:** System logs protect user confidentiality  

---

## 10. Performance Requirements

**REQ-PERF-001:** Chat responses should be returned within a reasonable timeframe  
**REQ-PERF-002:** Page navigation should feel instantaneous  
**REQ-PERF-003:** The system should handle multiple simultaneous users  

---

## 11. Internationalization

**REQ-I18N-001:** The user interface is fully available in Chinese and English  
**REQ-I18N-002:** Users can switch language preference in settings  
**REQ-I18N-003:** TCM terminology is consistently translated with original Chinese/拼音 preserved  
**REQ-I18N-004:** Content respects regional context (e.g., herb availability notes)  

---

## 12. Out of Scope for v1

The following features are identified but deferred to future versions:

| Feature | Deferred To |
|---------|-------------|
| Professional license verification workflow | v2 |
| Full expert case contribution and review workflow | v2 |
| Payment processing and subscription management | v2 |
| Mobile application | v2 |
| Third-party API access | v2 |
| Advanced analytics and reporting | v2 |
| Multi-language beyond Chinese/English | v3 |
| Integration with EHR/medical record systems | v3 |

---

## 13. v1 Success Criteria

- Users can register, login, and manage their accounts
- Users can conduct AI-assisted clinical conversations in Chinese or English
- Users can browse and search formulas and classical clauses
- The system provides appropriate safety disclaimers and high-risk handling
- Admins can manage users and content
- The system is available in both Chinese and English
- Performance is acceptable for typical user loads
