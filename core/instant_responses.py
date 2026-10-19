# core/instant_responses.py
# ── Zero-latency response cache for MSU Corp customer support ──────────
#
# Any query matching a key here is answered INSTANTLY from RAM.
# No embedding, no vector search, no LLM call needed.
# Average response time: < 1ms

import re
from utils.logger import log

_BOT_NAME  = "MSU Corp Support Assistant"
_ORG       = "MSU Corp"
_PLATFORM  = "MSU Corp platform"

# ── Pre-built response library ────────────────────────────────────────
# Keys: lowercase cleaned query → instant markdown reply
INSTANT_CACHE: dict[str, str] = {

    # ── Greetings ─────────────────────────────────────────────────────
    "hi":           f"Hi there! 👋 Welcome to **{_ORG} Support**. How can I help you today?",
    "hello":        f"Hello! 😊 Welcome to **{_ORG} Support**. What issue can I help you with?",
    "hey":          f"Hey! 👋 I'm the **{_BOT_NAME}**. Describe the issue you're facing and I'll get you sorted!",
    "hi there":     f"Hi there! 👋 You've reached **{_ORG} Support**. How can I assist you?",
    "hey there":    f"Hey there! 😊 I'm here to help resolve your **{_ORG}** platform issues!",
    "hello there":  f"Hello! 😊 This is **{_ORG} Support**. What can I help you with today?",
    "good morning": f"Good morning! ☀️ Welcome to **{_ORG} Support**. How can I help you?",
    "good afternoon": f"Good afternoon! 🌤️ Welcome to **{_ORG} Support**. What's the issue?",
    "good evening": f"Good evening! 🌙 You've reached **{_ORG} Support**. How can I assist?",
    "good night":   f"Good night! 🌙 **{_ORG} Support** is available 24/7 — feel free to ask anytime!",
    "greetings":    f"Greetings! 🙏 This is **{_ORG} Support**. What can I do for you today?",
    "howdy":        f"Howdy! 🤠 Welcome to **{_ORG} Support**. What issue are you experiencing?",
    "yo":           f"Hey! 👋 **{_ORG} Support** here. Got an issue? Let's fix it! 💡",
    "sup":          f"Hey! **{_ORG} Support** here. Having a problem with the platform? Let me help! 💡",
    "whats up":     f"Not much! 😄 I'm the **{_BOT_NAME}**, ready to resolve your platform issues!",
    "what's up":    f"Not much! 😄 I'm the **{_BOT_NAME}**, ready to resolve your platform issues!",

    # ── Identity / Who are you ─────────────────────────────────────────
    "who are you": (
        f"I'm the **{_BOT_NAME}** 🤖 — an AI-powered chat support agent for **{_ORG}**.\n\n"
        "I'm here to help you resolve issues, answer queries, and guide you through the platform — "
        "without waiting for a human support agent. Just describe your problem and I'll help!"
    ),
    "what are you": (
        f"I'm an **AI-powered customer support bot** for **{_ORG}** 🤖.\n\n"
        "I use the official {_ORG} support knowledge base to answer your questions and help "
        "troubleshoot platform issues instantly — no hold times, no ticket queues."
    ),
    "what is your name":  f"I'm the **{_BOT_NAME}** 😊. Describe your issue and I'll help right away!",
    "what's your name":   f"I'm the **{_BOT_NAME}** 😊. What issue can I help you resolve today?",
    "tell me your name":  f"I'm the **{_BOT_NAME}**! I'm here to resolve your {_ORG} platform issues.",
    "what do i call you": f"You can call me the **{_BOT_NAME}**! 😊 What can I help you with?",
    "who am i talking to": (
        f"You're chatting with the **{_BOT_NAME}** 🤖 — {_ORG}'s automated L1 support assistant.\n\n"
        "I can resolve most common platform issues instantly using the {_ORG} support knowledge base."
    ),
    "are you a bot": (
        f"Yes, I'm an AI-powered support bot 🤖 for **{_ORG}**! "
        "I'm designed to replace L1 human support — resolving your platform issues quickly and accurately, 24/7."
    ),
    "are you a human": (
        "No, I'm an AI support assistant 🤖! But I'm trained on the full **{_ORG} support knowledge base** "
        "and I can handle most platform issues just as effectively — often faster than a human agent!"
    ),
    "are you ai":   f"Yes! I'm an AI-powered support assistant 🤖 for **{_ORG}**. How can I help you today?",
    "are you real": f"I'm a real AI! 🤖 Powered by the **{_ORG}** support knowledge base. Ready to help!",
    "are you chatgpt": (
        f"No, I'm not ChatGPT. I'm the **{_BOT_NAME}** — a private AI assistant that only uses "
        f"**{_ORG}'s own support documents** to answer your questions. 🔒"
    ),

    # ── Who built you ─────────────────────────────────────────────────
    "who built you":    f"I was built by the **{_ORG} tech team** to automate L1 customer support. 🛠️",
    "who made you":     f"I was created by **{_ORG}** to provide instant, 24/7 platform support to customers. 🛠️",
    "who created you":  f"I was created by **{_ORG}** as an AI-powered customer support assistant. 💡",
    "who developed you": f"I was developed by the **{_ORG}** team to resolve customer platform issues automatically. 💻",
    "how were you made": (
        f"I was built using **RAG (Retrieval-Augmented Generation)** technology. "
        f"The **{_ORG}** support documents are indexed in a vector database, and I search them "
        "in real time to give you accurate, grounded answers to your platform questions. 🧠"
    ),
    "how do you work": (
        f"When you ask me a question, I **search the {_ORG} support knowledge base** for "
        "relevant information and compose an accurate answer based on the official documents. "
        "Everything runs privately within the {_ORG} infrastructure — no data leaves the system. 🔒"
    ),

    # ── How are you / Small talk ──────────────────────────────────────
    "how are you":             f"I'm running great, thanks for asking! 😊 Ready to help with any {_ORG} platform issues. What's the problem?",
    "how are you doing":       f"All systems go! 😊 Ready to resolve your {_ORG} support queries. What can I help with?",
    "how is it going":         f"Going well! 😄 How can I assist you with the {_ORG} platform today?",
    "how are things":          f"Things are good! 😊 I'm here and ready to help with your {_ORG} issues. What's going on?",
    "i hope you are doing well": f"Thank you! 😊 I'm always up and running. What {_ORG} issue can I help you solve?",
    "you doing good":          "Yes, doing great! 😄 What can I help you resolve today?",
    "doing good":              "Always at 100%! 😊 What's the issue you're facing on the platform?",

    # ── What can you do / Help ────────────────────────────────────────
    "what can you do": (
        f"I'm the **{_BOT_NAME}** and here's how I can help you 💡:\n\n"
        f"- 🔧 **Platform Issues** — Errors, bugs, and unexpected behaviour on the {_ORG} platform\n"
        "- 🔑 **Account & Access** — Login issues, password resets, account setup\n"
        "- 📋 **Feature Guidance** — How to use specific platform features and modules\n"
        "- 🔄 **Integration Help** — Connecting third-party tools or APIs with the platform\n"
        "- 📊 **Data & Reports** — Exporting data, report generation, dashboard issues\n"
        "- ⚙️ **Configuration** — Platform settings, permissions, and admin configurations\n"
        "- 📄 **Policy & Procedures** — Company support guidelines and escalation paths\n\n"
        "Just describe your issue in plain language and I'll help you resolve it!"
    ),
    "what can you help with": (
        f"I can help you with any issues you face on the **{_ORG} platform** 👇:\n\n"
        "- 🔧 Troubleshooting platform errors and bugs\n"
        "- 🔑 Account login, access, and permission issues\n"
        "- 📋 Understanding and using platform features\n"
        "- 🔄 Integration and API-related questions\n"
        "- 📊 Reports, dashboards, and data export help\n"
        "- ⚙️ Configuration and admin settings\n\n"
        "Describe your issue and I'll find the answer from the support knowledge base!"
    ),
    "what are you capable of": (
        f"Here's what I'm capable of as the **{_BOT_NAME}** 💪:\n\n"
        f"✅ Resolving common {_ORG} platform issues instantly\n"
        "✅ Answering questions based on official support documentation\n"
        "✅ Guiding you step-by-step through troubleshooting\n"
        "✅ Explaining platform features and workflows\n"
        "✅ 24/7 availability — no wait times\n\n"
        "⚠️ For complex issues not covered by the knowledge base, I'll guide you on how to escalate."
    ),
    "what are your capabilities": (
        f"As the **{_BOT_NAME}**, I can:\n\n"
        f"✅ Search the {_ORG} support knowledge base in real time\n"
        "✅ Diagnose and troubleshoot platform errors\n"
        "✅ Explain features, configurations, and workflows\n"
        "✅ Handle account and access-related queries\n"
        "✅ Operate 24/7 with instant responses\n\n"
        "The more support documents are loaded, the smarter I get!"
    ),
    "help": (
        f"Sure! Here's how **{_BOT_NAME}** works 👇:\n\n"
        f"1. **Describe your issue** — e.g. *'I can't log in to my account'* or *'The dashboard is showing an error'*\n"
        f"2. I'll **search the {_ORG} support knowledge base** and find the best answer\n"
        "3. You'll get a detailed response with the relevant steps to resolve your issue\n"
        "4. Click **'View Source Chunks'** to see the original support document excerpts\n\n"
        "What issue are you facing right now?"
    ),
    "i need help":      f"Of course! 😊 Please describe the issue you're facing on the **{_ORG} platform** and I'll help you resolve it right away.",
    "need help":        f"Sure thing! 😊 Tell me what's happening on the **{_ORG} platform** and I'll get it sorted.",
    "i have a problem": f"I'm sorry to hear that! 😟 Please describe the problem you're facing and I'll do my best to help resolve it.",
    "i have an issue":  f"Let's fix it! 🔧 Please describe the issue you're experiencing on the **{_ORG} platform**.",
    "i am facing an issue": f"I'm here to help! 🔧 Please tell me what issue you're facing on the **{_ORG} platform**.",
    "something is not working": f"Let's figure out what's going on! 🔧 Please describe what's not working and I'll search the knowledge base for a solution.",

    # ── Thanks / Goodbye ─────────────────────────────────────────────
    "thanks":           f"You're welcome! 😊 Glad I could help. Is there anything else about the {_ORG} platform I can assist with?",
    "thank you":        f"You're welcome! 😊 Happy to help. Feel free to return if you face any other issues on the {_ORG} platform!",
    "thank you so much": f"You're very welcome! 😊 Don't hesitate to reach out if you need more support!",
    "thanks a lot":     f"No problem at all! 😊 {_ORG} Support is here whenever you need us.",
    "bye":              f"Goodbye! 👋 Come back anytime you need **{_ORG} Support**!",
    "goodbye":          f"Goodbye! 👋 Have a great day. **{_ORG} Support** is here whenever you need us!",
    "see you":          f"See you! 👋 Don't hesitate to return if you need {_ORG} support.",
    "see you later":    "See you later! 👋 Take care!",
    "take care":        f"You too! 😊 {_ORG} Support is here 24/7 whenever you need us.",
    "ok":               "Got it! 😊 Is there anything else I can help you with?",
    "okay":             "Alright! 😊 Feel free to ask if you have more questions.",
    "cool":             "Glad I could help! 😊 Anything else you need?",
    "great":            "Great! 😊 Let me know if you run into any other issues!",
    "awesome":          "Awesome! 😄 Anything else I can help you with today?",
    "nice":             "Thanks! 😊 Feel free to ask if you need more help.",
    "perfect":          "Perfect! 😊 Don't hesitate to reach out again if the issue comes back.",
    "issue resolved":   f"Fantastic! 🎉 Glad we could resolve that for you. Feel free to come back to **{_ORG} Support** anytime!",
    "problem solved":   f"Great to hear! 🎉 If you ever face another issue on the {_ORG} platform, I'm here to help!",
    "it worked":        f"Excellent! 🎉 Happy to hear the issue is resolved. **{_ORG} Support** is here whenever you need us!",
    "it works now":     f"That's great! 😊 If you run into anything else, just reach out to **{_ORG} Support**.",

    # ── Test ──────────────────────────────────────────────────────────
    "test":        f"✅ I'm working! **{_BOT_NAME}** is online and ready to assist.",
    "ping":        "🏓 Pong! The MSU Corp Support Assistant is online.",
    "hello world": f"Hello! 🌍 **{_BOT_NAME}** is live and ready to help customers!",
}

# ── Flexible regex patterns ────────────────────────────────────────────
_PATTERN_RESPONSES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^(hi+|hii+|hiii+|helo|hellow|heya?)[\s!?.,]*$"),
     f"Hi there! 👋 Welcome to **{_ORG} Support**. What issue can I help you with today?"),

    (re.compile(r"^(how are (you|u)( doing| today)?)\??$"),
     f"I'm running great, thanks! 😊 Ready to resolve your **{_ORG}** platform issues. What's the problem?"),

    (re.compile(r"^(what is|what's) your name\??$"),
     f"I'm the **{_BOT_NAME}** 😊. Describe your issue and I'll get it sorted!"),

    (re.compile(r"^who (are|r) (you|u)\??$"),
     f"I'm the **{_BOT_NAME}** 🤖 — {_ORG}'s AI-powered L1 support assistant. How can I help?"),

    (re.compile(r"^who (built|made|created|developed) (you|u)\??$"),
     f"I was built by the **{_ORG} team** to provide instant, 24/7 platform support to customers. 🛠️"),

    (re.compile(r"^(what can you|what do you) (do|help with|assist with)\??$"),
     f"I can help resolve **{_ORG} platform issues** — login problems, errors, feature questions, and more! Describe your issue and I'll help. 💡"),

    (re.compile(r"^(good|gd) (morning|afternoon|evening|night|day)[\s!?.,]*$"),
     f"Good day! ☀️ Welcome to **{_ORG} Support**. What issue can I help you with?"),

    (re.compile(r"^(thank(s| you)( so much| a lot| very much)?|ty|thx)[\s!?.,]*$"),
     f"You're welcome! 😊 Is there anything else about the **{_ORG}** platform I can help with?"),

    (re.compile(r"^(bye|goodbye|good bye|cya|see (you|ya)( later)?)[\s!?.,]*$"),
     f"Goodbye! 👋 **{_ORG} Support** is here whenever you need us!"),

    (re.compile(r"^(are you|r u) (a )?(bot|robot|ai|artificial intelligence|chatbot)\??$"),
     f"Yes! I'm an AI-powered support bot 🤖 for **{_ORG}** — available 24/7 to resolve your platform issues instantly."),

    (re.compile(r"^(are you|r u) (a )?human\??$"),
     f"No, I'm an AI! 🤖 But I'm powered by **{_ORG}'s** official support knowledge base and can resolve most issues just like a human agent — often faster!"),

    (re.compile(r"^(what is|what's) (the )?time\??$"),
     "I don't have access to real-time clock data, but your device's taskbar shows the current time! ⏰"),

    (re.compile(r"^i (have|am having|am facing) (a |an )?(issue|problem|error|bug|trouble)[\s\w]*$"),
     f"I'm here to help! 🔧 Please describe the issue you're experiencing on the **{_ORG} platform** in detail and I'll search our knowledge base for a solution."),

    (re.compile(r"^(tell me )?a joke[\s!?.,]*$"),
     f"Why did the platform throw an error? Because it couldn't handle the **load**! 😄 Now let's get your real issue sorted — what's the problem?"),
]


def _clean(text: str) -> str:
    """Normalize query for cache lookup."""
    return re.sub(r"\s+", " ", text.strip().lower()).strip("!.,?\"' ")


def get_instant_response(query: str) -> str | None:
    """
    Check if query matches any instant-response pattern.
    Returns the cached answer string, or None if no match found.
    Average time: < 1ms
    """
    cleaned = _clean(query)

    # 1. Exact dictionary lookup (O(1))
    if cleaned in INSTANT_CACHE:
        log.info(f"[Instant] Cache hit (exact): '{cleaned}'")
        return INSTANT_CACHE[cleaned]

    # 2. Regex pattern matching
    for pattern, response in _PATTERN_RESPONSES:
        if pattern.match(cleaned):
            log.info(f"[Instant] Cache hit (regex): '{cleaned}'")
            return response

    return None
