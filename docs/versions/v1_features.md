# Version 1: Core Knowledge Foundation

A focused Shang Han Lun reference tool with bilingual support and basic exploration features.

---

## Overview

Shanghan-TCM Evidence is a nonprofit project initiated by WASFS, designed as a secure, expert-level assistant centered on classical Traditional Chinese Medicine, starting with the Treatise on Cold Damage (Shang Han Lun).

The system combines curated classical texts with structured formula knowledge, providing clinical decision support for trained TCM professionals and learning support for students and practitioners.

Primary use cases:
- Clinical decision support for trained TCM professionals
- Learning and teaching support for students and practitioners
- Bilingual (Chinese-English) access for users in North America and worldwide

---

## Knowledge Features

### Complete Shang Han Lun
- Full classical Chinese text of the Shang Han Lun (Treatise on Cold Damage)
- Source and edition metadata for all passages
- Authoritative English translations where available
- Clear attribution to original sources

### 112 Original Prescriptions
- All 112 formulas from the Shang Han Lun
- Complete composition listings (all herbs and dosages)
- Roles of ingredients (jun/chen/zuo/shi - monarch, minister, assistant, envoy)
- Functions and therapeutic indications
- Common modifications and adjustments
- Cautions and contraindications

### Structured Clauses
- All 112 clauses organized by the original 112 prescriptions
- Pattern diagnosis information for each clause
- Symptom presentations and manifestations
- Formula-text relationships preserved
- Clinical application guidance

### Bilingual Content
- Original Chinese text throughout
- English translations for all content
- Bilingual terminology with standardized glossary
- Support for queries in either language

---

## Interface Features

### Home Page
- Project introduction and overview
- Description of AI assistant capabilities
- Clear call-to-action to sign in
- Nonprofit attribution (WASFS)

### Authentication
- Professional-only access (no guest accounts)
- Email/password login
- Session-based authentication
- Secure logout functionality
- User session display in header

### Chatbot (Primary Interface)
The chatbot is the main way users interact with the system:

**Input:**
- Free-text questions in Chinese or English
- Enter key or button to submit
- Shift+Enter for multi-line input
- Auto-focus on input field

**Output:**
- AI-generated responses based on Shang Han Lun knowledge
- Clear, professional answers
- Source references displayed with each response
- Bilingual responses (matches input language when possible)

**Sources/References:**
- Each answer shows relevant source material
- Citations to specific chapters/clauses
- Formula references when applicable
- Traceable to original classical text

**Feedback System:**
After each bot response, users can provide feedback:
- **Thumb Up**: Indicates the answer was helpful and accurate
- **Thumb Down**: Indicates the answer was not helpful or inaccurate
- **Optional Feedback Popup**: Clicking thumb down (or optionally thumb up) opens a popup with:
  - Text input field for detailed feedback comments
  - Submit button to send feedback
  - Skip button to close without submitting
- Feedback is submitted asynchronously without disrupting the conversation
- Simple thumbs icons appear below each bot message

**User Experience:**
- Welcome message with usage instructions
- Typing indicator while processing
- Chat history within session
- Smooth scroll to latest message

---

## Data Storage & Admin Access

### Feedback Storage
- Each feedback submission is saved as a JSON file
- File naming: `feedback_{timestamp}_{user_hash}.json`
- Contents include: rating (thumb up/down), optional feedback text, message ID, timestamp, user email
- Stored in `/data/feedback/` directory on the server

### Conversation Storage
- Chat sessions are logged with user consent
- File naming: `conversation_{session_id}_{date}.json`
- Contents include: all messages (user queries and bot responses), sources cited, session start/end times, user email
- Stored in `/data/conversations/` directory on the server
- Sessions are archived after user logout

### Admin Access
- All feedback and conversation files are accessible via SSH
- Files stored in plain JSON format for easy inspection
- Admin users can SSH into the server and read files directly from `/data/feedback/` and `/data/conversations/`
- No web-based admin interface in v1 - file-based access only
- Directory structure:
  ```
  /data/
  ├── feedback/
  │   └── feedback_20260101_120000_prof@tcm.org.json
  └── conversations/
      └── conv_abc123_2026-01-01.json
  ```

---

## User Flow

1. **Landing**: User visits home page → sees overview → clicks "Sign In"
2. **Login**: User enters professional credentials → authenticated → redirected to chat
3. **Chat**: User asks questions → receives AI answers with sources → can continue chatting
4. **Logout**: User clicks "Sign Out" → session cleared → returns to home page

---

## Design Principles

1. **Simplicity**: Only three pages - home, login, chat
2. **Professional**: Clean, clinical aesthetic appropriate for TCM professionals
3. **Bilingual**: Full support for Chinese and English throughout
4. **Source-focused**: Every answer includes references to source material
5. **Secure**: Professional-only access with authenticated sessions
