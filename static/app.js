/* Samajh front-end: documents, forms, tracking, recommendations, centres.
   No framework, no inline handlers (CSP-safe), delegated events throughout. */

const $ = (id) => document.getElementById(id);

const state = {
  lang: localStorage.getItem("samajh_lang") || "en",
  langs: { en: "English", hi: "हिंदी", mr: "मराठी" },
  locales: { en: "en-IN", hi: "hi-IN", mr: "mr-IN" },
  imageFile: null,
  lastAnalysis: null,
  lastSheet: null,
  busy: false,
  user: null,
  alerts: [],
  comfort: {
    size: Number(localStorage.getItem("samajh_size") || 100),
    contrast: localStorage.getItem("samajh_contrast") === "1",
    spacing: localStorage.getItem("samajh_spacing") === "1",
    autospeak: localStorage.getItem("samajh_autospeak") === "1",
  },
};

/* ============================== i18n ============================== */

const I18N = {
  en: {
    "tab.doc": "Read a document",
    "tab.forms": "Forms & guide",
    "tab.track": "My paperwork",
    "tab.foryou": "For you",
    "tab.centres": "Find a centre",
    "nav.signin": "Sign in",
    "doc.dropTitle": "Drop the document here",
    "doc.dropHint": "A bill, notice, agreement, letter or circular. Drag and drop, click, paste, or",
    "doc.camera": "use your phone camera",
    "doc.change": "Choose a different document",
    "doc.saveVault": "Save to my vault",
    "doc.pdf": "Download checklist PDF",
    "doc.saveToggle": "Keep this scan in my encrypted vault (auto-deletes after 30 days)",
    "doc.privacy": "Processed in memory. If you sign in and save, the scan is encrypted with a key only your account can open.",
    "doc.kicker": "The reading desk",
    "doc.lede": "Upload a document on the left. Samajh reads it with Gemma 4 and explains what it says, what it asks of you, and by when — in your language.",
    "doc.loading": "Reading the document…",
    "vault.title": "My vault",
    "vault.deleteAll": "Delete all stored scans",
    "forms.intro": "Ask about a government form, scheme or office. Samajh answers only from a verified knowledge base, tells you which documents are compulsory and which are optional, what extra costs to expect, where to go, and warns you about scams. It says honestly when it does not have verified information.",
    "forms.ask": "Your question",
    "forms.send": "Ask",
    "forms.checking": "Checking the records…",
    "track.gate": "Sign in to track your applications — the status of the process, deadlines, warnings and what to do next, so the paperwork keeps moving.",
    "track.title": "Applications in progress",
    "track.add": "Track new paperwork",
    "track.formLabel": "What are you applying for?",
    "track.custom": "Something else (type below)",
    "track.nameLabel": "Name (if not in the list)",
    "track.officeLabel": "Office / centre involved",
    "track.refLabel": "Reference / acknowledgement number",
    "track.dateLabel": "Target date (YYYY-MM-DD)",
    "track.remindLabel": "Warn me this many days before",
    "track.notesLabel": "Notes for yourself",
    "track.save": "Start tracking",
    "common.cancel": "Cancel",
    "foryou.gate": "Sign in to get recommendations for your situation — farmer, government employee, doctor, student, senior, worker or business owner. Schemes, benefits, extra costs and the forms to fill.",
    "foryou.title": "Schemes and benefits for you",
    "foryou.iam": "I am a",
    "foryou.also": "Also useful for everyone",
    "centres.title": "Where do I have to go?",
    "centres.lede": "Search the office directory by service and area. This is a sample directory — always confirm the address and hours on the official portal before travelling.",
    "centres.service": "Service",
    "centres.area": "Area, district or state",
    "centres.search": "Search centres",
    "centres.any": "Any service",
    "centres.none": "No centre found for that search. Try a different district or service.",
    "centres.maps": "Open in Maps",
    "centres.services": "Services",
    "privacy.link": "Privacy & security",
    "auth.title": "Your Samajh account",
    "auth.signin": "Sign in",
    "auth.register": "Create account",
    "auth.email": "Email",
    "auth.password": "Password",
    "auth.name": "Your name",
    "auth.role": "I am a",
    "auth.area": "Area / district (for centres and recommendations)",
    "auth.phone": "Phone (optional)",
    "auth.consent": "I understand Samajh stores only what I choose to save, encrypted, and that I can delete my account and data at any time.",
    "auth.note": "Your scans are encrypted with a key only your account can open. You can export or erase everything from the Account panel.",
    "account.title": "Account & privacy",
    "account.signedOut": "You are browsing as a guest. Nothing is stored unless you create an account. Sign in to keep an encrypted vault, track applications and get recommendations.",
    "account.saveProfile": "Save profile",
    "account.changePassword": "Change password",
    "account.currentPassword": "Current password",
    "account.newPassword": "New password (8+ characters)",
    "account.privacyTitle": "Privacy & security",
    "account.export": "Download my data (JSON)",
    "account.logout": "Sign out",
    "account.delete": "Delete account and all data",
    "account.deleteConfirm": "This deletes your account, every stored scan, application and alert. This cannot be undone. Continue?",
    "alerts.title": "Alerts and warnings",
    "alerts.empty": "Nothing needs attention right now. Deadlines from your scans and tracked applications appear here.",
    "alerts.add": "Set a reminder",
    "alerts.what": "What should we remind you about?",
    "alerts.when": "Date (YYYY-MM-DD)",
    "alerts.save": "Save reminder",
    "alerts.dismiss": "Done",
    "alerts.delete": "Delete",
    "comfort.title": "Comfort settings",
    "comfort.size": "Text size",
    "comfort.contrast": "High contrast",
    "comfort.spacing": "Easy-reading spacing",
    "comfort.autospeak": "Read answers aloud automatically (text to speech)",
    "comfort.ttsNote": "Text to speech uses your device's voices. You can also press \"Read aloud\" on any answer.",
    "btn.read": "Read aloud",
    "btn.stop": "Stop reading",
    "btn.view": "Open",
    "btn.reread": "Read again",
    "btn.download": "Download",
    "btn.delete": "Delete",
    "btn.pdf": "Checklist PDF",
    "btn.track": "Track this process",
    "status.started": "Started",
    "status.documents_gathered": "Documents gathered",
    "status.submitted": "Submitted",
    "status.under_review": "Under review",
    "status.action_needed": "Action needed from you",
    "status.approved": "Approved",
    "status.rejected": "Rejected",
    "status.completed": "Completed",
    "sheet.compulsory": "Compulsory documents",
    "sheet.optional": "Optional / extra documents",
    "sheet.costs": "Costs involved",
    "sheet.where": "Where to go",
    "sheet.processing": "How long it takes",
    "sheet.warnings": "Warnings — stay safe",
    "sheet.steps": "Steps in order",
    "sheet.verify": "Always verify on the official portal before you act.",
    "analysis.actions": "What to do",
    "analysis.deadlines": "Deadlines",
    "analysis.flags": "Watch out for",
    "analysis.verdicts": "Two honest verdicts",
    "analysis.canIgnore": "You can set this aside:",
    "analysis.needsAttention": "This needs attention:",
    "analysis.pro": "A professional may help:",
    "analysis.noPro": "No professional needed:",
    "analysis.facts": "Key facts",
    "analysis.saved": "Encrypted copy saved to your vault.",
    "analysis.overdue": "OVERDUE",
    "analysis.actby": "ACT BY",
    "analysis.actsoon": "ACT SOON",
    "analysis.ignore": "CAN BE IGNORED",
    "analysis.onfile": "ON FILE",
    "urgency.now": "do now",
    "urgency.soon": "do soon",
    "urgency.later": "when you can",
    "days.past": "days past",
    "days.today": "today",
    "days.left": "days left",
    "vault.empty": "No saved scans yet. Toggle \"Keep this scan\" before uploading.",
    "vault.expires": "auto-deletes",
    "err.reach": "Could not reach the service. Check your connection and try again.",
    "err.generic": "Something went wrong. Please try again.",
    "toast.saved": "Saved.",
    "toast.deleted": "Deleted.",
    "foryou.benefits": "What you get",
    "foryou.eligibility": "Who can apply",
    "foryou.documents": "Documents to keep ready",
    "foryou.costs": "Extra costs to plan for",
    "foryou.where": "Where to go",
    "foryou.forms": "Forms to fill in Samajh",
    "foryou.steps": "Steps in order",
    "foryou.warnings": "Warnings",
    "foryou.official": "Official portal",
    "roles.citizen": "General citizen",
    "roles.farmer": "Farmer",
    "roles.govt_employee": "Government service employee",
    "roles.doctor": "Doctor",
    "roles.student": "Student",
    "roles.senior_citizen": "Senior citizen",
    "roles.entrepreneur": "Business owner / entrepreneur",
    "roles.worker": "Worker (unorganised sector)",
  },
  hi: {
    "tab.doc": "दस्तावेज़ पढ़ें",
    "tab.forms": "फ़ॉर्म और मार्गदर्शन",
    "tab.track": "मेरा कागज़ी काम",
    "tab.foryou": "आपके लिए",
    "tab.centres": "केंद्र खोजें",
    "nav.signin": "साइन इन",
    "doc.dropTitle": "दस्तावेज़ यहाँ छोड़ें",
    "doc.dropHint": "बिल, नोटिस, एग्रीमेंट, चिट्ठी या सर्कुलर। ड्रैग करें, क्लिक करें, पेस्ट करें, या",
    "doc.camera": "फ़ोन का कैमरा इस्तेमाल करें",
    "doc.change": "दूसरा दस्तावेज़ चुनें",
    "doc.saveVault": "मेरे वॉल्ट में सहेजें",
    "doc.pdf": "चेकलिस्ट PDF डाउनलोड करें",
    "doc.saveToggle": "इस स्कैन को मेरे एन्क्रिप्टेड वॉल्ट में रखें (30 दिन बाद अपने-आप हट जाएगा)",
    "doc.privacy": "प्रोसेसिंग मेमोरी में होती है। साइन इन करके सहेजें तो स्कैन ऐसी चाबी से एन्क्रिप्ट होता है जो सिर्फ़ आपका अकाउंट खोल सकता है।",
    "doc.kicker": "रीडिंग डेस्क",
    "doc.lede": "बाईं ओर दस्तावेज़ अपलोड करें। Samajh उसे Gemma 4 से पढ़कर आपकी भाषा में समझाता है — क्या लिखा है, आपसे क्या चाहता है, और कब तक।",
    "doc.loading": "दस्तावेज़ पढ़ा जा रहा है…",
    "vault.title": "मेरा वॉल्ट",
    "vault.deleteAll": "सभी सहेजे स्कैन हटाएँ",
    "forms.intro": "किसी सरकारी फ़ॉर्म, योजना या दफ़्तर के बारे में पूछें। Samajh सिर्फ़ सत्यापित जानकारी से जवाब देता है — कौन-से दस्तावेज़ ज़रूरी हैं, कौन-से वैकल्पिक, कितना ख़र्च आएगा, कहाँ जाना है, और धोखाधड़ी की चेतावनी।",
    "forms.ask": "आपका सवाल",
    "forms.send": "पूछें",
    "forms.checking": "रिकॉर्ड देखे जा रहे हैं…",
    "track.gate": "साइन इन करें और अपने आवेदन ट्रैक करें — प्रक्रिया की स्थिति, समय-सीमा, चेतावनी और आगे क्या करना है।",
    "track.title": "चल रहे आवेदन",
    "track.add": "नया कागज़ी काम ट्रैक करें",
    "track.formLabel": "आप किस चीज़ के लिए आवेदन कर रहे हैं?",
    "track.custom": "कुछ और (नीचे लिखें)",
    "track.nameLabel": "नाम (अगर सूची में नहीं है)",
    "track.officeLabel": "संबंधित दफ़्तर / केंद्र",
    "track.refLabel": "संदर्भ / पावती नंबर",
    "track.dateLabel": "लक्ष्य तिथि (YYYY-MM-DD)",
    "track.remindLabel": "कितने दिन पहले चेतावनी दें",
    "track.notesLabel": "अपने लिए नोट",
    "track.save": "ट्रैकिंग शुरू करें",
    "common.cancel": "रद्द करें",
    "foryou.gate": "साइन इन करें और अपनी स्थिति के अनुसार सुझाव पाएँ — किसान, सरकारी कर्मचारी, डॉक्टर, छात्र, वरिष्ठ नागरिक, श्रमिक या व्यवसायी। योजनाएँ, लाभ, ख़र्च और भरने वाले फ़ॉर्म।",
    "foryou.title": "आपके लिए योजनाएँ और लाभ",
    "foryou.iam": "मैं हूँ",
    "foryou.also": "सबके लिए उपयोगी",
    "centres.title": "मुझे कहाँ जाना है?",
    "centres.lede": "सेवा और इलाक़े से दफ़्तरों की सूची में खोजें। यह नमूना सूची है — जाने से पहले पते और समय की पुष्टि आधिकारिक पोर्टल पर करें।",
    "centres.service": "सेवा",
    "centres.area": "इलाक़ा, ज़िला या राज्य",
    "centres.search": "केंद्र खोजें",
    "centres.any": "कोई भी सेवा",
    "centres.none": "इस खोज के लिए कोई केंद्र नहीं मिला। दूसरा ज़िला या सेवा आज़माएँ।",
    "centres.maps": "मैप में खोलें",
    "centres.services": "सेवाएँ",
    "privacy.link": "निजता और सुरक्षा",
    "auth.title": "आपका Samajh अकाउंट",
    "auth.signin": "साइन इन",
    "auth.register": "अकाउंट बनाएँ",
    "auth.email": "ईमेल",
    "auth.password": "पासवर्ड",
    "auth.name": "आपका नाम",
    "auth.role": "मैं हूँ",
    "auth.area": "इलाक़ा / ज़िला (केंद्र और सुझाव के लिए)",
    "auth.phone": "फ़ोन (वैकल्पिक)",
    "auth.consent": "मैं समझता/समझती हूँ कि Samajh सिर्फ़ वही सहेजता है जो मैं चुनता/चुनती हूँ, एन्क्रिप्ट करके, और मैं कभी भी अकाउंट और डेटा मिटा सकता/सकती हूँ।",
    "auth.note": "आपके स्कैन ऐसी चाबी से एन्क्रिप्ट हैं जो सिर्फ़ आपका अकाउंट खोल सकता है। अकाउंट पैनल से पूरा डेटा डाउनलोड या मिटाया जा सकता है।",
    "account.title": "अकाउंट और निजता",
    "account.signedOut": "आप मेहमान के रूप में देख रहे हैं। अकाउंट बनाए बिना कुछ भी सहेजा नहीं जाता। साइन इन करें — एन्क्रिप्टेड वॉल्ट, ट्रैकिंग और सुझावों के लिए।",
    "account.saveProfile": "प्रोफ़ाइल सहेजें",
    "account.changePassword": "पासवर्ड बदलें",
    "account.currentPassword": "मौजूदा पासवर्ड",
    "account.newPassword": "नया पासवर्ड (8+ अक्षर)",
    "account.privacyTitle": "निजता और सुरक्षा",
    "account.export": "मेरा डेटा डाउनलोड करें (JSON)",
    "account.logout": "साइन आउट",
    "account.delete": "अकाउंट और सारा डेटा मिटाएँ",
    "account.deleteConfirm": "इससे आपका अकाउंट, हर सहेजा स्कैन, आवेदन और अलर्ट मिट जाएगा। इसे वापस नहीं लाया जा सकता। जारी रखें?",
    "alerts.title": "अलर्ट और चेतावनियाँ",
    "alerts.empty": "अभी किसी चीज़ पर ध्यान देने की ज़रूरत नहीं। आपके स्कैन और आवेदनों की समय-सीमाएँ यहाँ दिखेंगी।",
    "alerts.add": "रिमाइंडर लगाएँ",
    "alerts.what": "किस बात की याद दिलाएँ?",
    "alerts.when": "तारीख़ (YYYY-MM-DD)",
    "alerts.save": "रिमाइंडर सहेजें",
    "alerts.dismiss": "हो गया",
    "alerts.delete": "हटाएँ",
    "comfort.title": "आराम सेटिंग्स",
    "comfort.size": "अक्षर का आकार",
    "comfort.contrast": "हाई कंट्रास्ट",
    "comfort.spacing": "पढ़ने में आसान स्पेसिंग",
    "comfort.autospeak": "जवाब अपने-आप पढ़कर सुनाएँ (टेक्स्ट टू स्पीच)",
    "comfort.ttsNote": "टेक्स्ट टू स्पीच आपके डिवाइस की आवाज़ें इस्तेमाल करता है। किसी भी जवाब पर \"पढ़कर सुनाएँ\" दबा सकते हैं।",
    "btn.read": "पढ़कर सुनाएँ",
    "btn.stop": "पढ़ना रोकें",
    "btn.view": "खोलें",
    "btn.reread": "फिर पढ़ें",
    "btn.download": "डाउनलोड",
    "btn.delete": "हटाएँ",
    "btn.pdf": "चेकलिस्ट PDF",
    "btn.track": "यह काम ट्रैक करें",
    "status.started": "शुरू",
    "status.documents_gathered": "दस्तावेज़ जुटाए",
    "status.submitted": "जमा",
    "status.under_review": "समीक्षा में",
    "status.action_needed": "आपसे कार्रवाई चाहिए",
    "status.approved": "स्वीकृत",
    "status.rejected": "अस्वीकृत",
    "status.completed": "पूरा",
    "sheet.compulsory": "ज़रूरी दस्तावेज़",
    "sheet.optional": "वैकल्पिक / अतिरिक्त दस्तावेज़",
    "sheet.costs": "लगने वाला ख़र्च",
    "sheet.where": "कहाँ जाना है",
    "sheet.processing": "कितना समय लगेगा",
    "sheet.warnings": "चेतावनियाँ — सावधान रहें",
    "sheet.steps": "क्रम में कदम",
    "sheet.verify": "काम करने से पहले आधिकारिक पोर्टल पर ज़रूर पुष्टि करें।",
    "analysis.actions": "क्या करना है",
    "analysis.deadlines": "समय-सीमाएँ",
    "analysis.flags": "इनसे सावधान",
    "analysis.verdicts": "दो साफ़ राय",
    "analysis.canIgnore": "इसे रख सकते हैं:",
    "analysis.needsAttention": "इस पर ध्यान चाहिए:",
    "analysis.pro": "विशेषज्ञ मदद कर सकता है:",
    "analysis.noPro": "किसी विशेषज्ञ की ज़रूरत नहीं:",
    "analysis.facts": "मुख्य तथ्य",
    "analysis.saved": "एन्क्रिप्टेड कॉपी आपके वॉल्ट में सहेज दी गई।",
    "analysis.overdue": "समय बीत गया",
    "analysis.actby": "इस तारीख़ तक",
    "analysis.actsoon": "जल्दी करें",
    "analysis.ignore": "नज़रअंदाज़ कर सकते हैं",
    "analysis.onfile": "फ़ाइल पर",
    "urgency.now": "अभी करें",
    "urgency.soon": "जल्दी करें",
    "urgency.later": "जब मौका मिले",
    "days.past": "दिन पहले",
    "days.today": "आज",
    "days.left": "दिन बाकी",
    "vault.empty": "अभी कोई स्कैन सहेजा नहीं है। अपलोड से पहले \"यह स्कैन रखें\" चुनें।",
    "vault.expires": "अपने-आप हटेगा",
    "err.reach": "सेवा तक नहीं पहुँच सके। कनेक्शन जाँचें और फिर कोशिश करें।",
    "err.generic": "कुछ गड़बड़ हुई। फिर कोशिश करें।",
    "toast.saved": "सहेजा गया।",
    "toast.deleted": "हटा दिया।",
    "foryou.benefits": "आपको क्या मिलेगा",
    "foryou.eligibility": "कौन आवेदन कर सकता है",
    "foryou.documents": "तैयार रखने वाले दस्तावेज़",
    "foryou.costs": "अतिरिक्त ख़र्च",
    "foryou.where": "कहाँ जाना है",
    "foryou.forms": "Samajh में भरने वाले फ़ॉर्म",
    "foryou.steps": "क्रम में कदम",
    "foryou.warnings": "चेतावनियाँ",
    "foryou.official": "आधिकारिक पोर्टल",
    "roles.citizen": "आम नागरिक",
    "roles.farmer": "किसान",
    "roles.govt_employee": "सरकारी कर्मचारी",
    "roles.doctor": "डॉक्टर",
    "roles.student": "छात्र",
    "roles.senior_citizen": "वरिष्ठ नागरिक",
    "roles.entrepreneur": "व्यवसायी / उद्यमी",
    "roles.worker": "श्रमिक (असंगठित)",
  },
  mr: {
    "tab.doc": "कागदपत्र वाचा",
    "tab.forms": "फॉर्म आणि मार्गदर्शन",
    "tab.track": "माझे काम",
    "tab.foryou": "तुमच्यासाठी",
    "tab.centres": "केंद्र शोधा",
    "nav.signin": "साइन इन",
    "doc.dropTitle": "कागदपत्र इथे टाका",
    "doc.dropHint": "बिल, नोटीस, करार, पत्र किंवा परिपत्रक. ड्रॅग करा, क्लिक करा, पेस्ट करा, किंवा",
    "doc.camera": "फोनचा कॅमेरा वापरा",
    "doc.change": "दुसरे कागदपत्र निवडा",
    "doc.saveVault": "माझ्या व्हॉल्टमध्ये जतन करा",
    "doc.pdf": "चेकलिस्ट PDF डाउनलोड करा",
    "doc.saveToggle": "हा स्कॅन माझ्या एन्क्रिप्टेड व्हॉल्टमध्ये ठेवा (30 दिवसांनी स्वतःहून हटेल)",
    "doc.privacy": "प्रक्रिया मेमरीमध्ये होते. साइन इन करून जतन केल्यास स्कॅन अशा कीने एन्क्रिप्ट होते जी फक्त तुमचे खाते उघडू शकते.",
    "doc.kicker": "वाचन टेबल",
    "doc.lede": "डावीकडे कागदपत्र अपलोड करा. Samajh ते Gemma 4 ने वाचून तुमच्या भाषेत समजावते — काय लिहिले आहे, तुमच्याकडून काय हवे, आणि कधापर्यंत.",
    "doc.loading": "कागदपत्र वाचले जात आहे…",
    "vault.title": "माझे व्हॉल्ट",
    "vault.deleteAll": "सर्व जतन केलेले स्कॅन हटवा",
    "forms.intro": "सरकारी फॉर्म, योजना किंवा कार्यालयाबद्दल विचारा. Samajh फक्त पडताळलेल्या माहितीवरून उत्तर देते — कोणती कागदपत्रे बंधनकारक, कोणती पर्यायी, किती खर्च, कुठे जायचे, आणि फसवणुकीच्या इशारा.",
    "forms.ask": "तुमचा प्रश्न",
    "forms.send": "विचारा",
    "forms.checking": "नोंदी तपासल्या जात आहेत…",
    "track.gate": "साइन इन करा आणि तुमचे अर्ज ट्रॅक करा — प्रक्रियेची स्थिती, मुदती, इशारे आणि पुढे काय करायचे.",
    "track.title": "चालू असलेले अर्ज",
    "track.add": "नवे काम ट्रॅक करा",
    "track.formLabel": "तुम्ही कशासाठी अर्ज करत आहात?",
    "track.custom": "दुसरे काही (खाली लिहा)",
    "track.nameLabel": "नाव (यादीत नसल्यास)",
    "track.officeLabel": "संबंधित कार्यालय / केंद्र",
    "track.refLabel": "संदर्भ / पोच क्रमांक",
    "track.dateLabel": "लक्ष्य तारीख (YYYY-MM-DD)",
    "track.remindLabel": "किती दिवस आधी इशारा द्यावा",
    "track.notesLabel": "स्वतःसाठी टिपा",
    "track.save": "ट्रॅकिंग सुरू करा",
    "common.cancel": "रद्द करा",
    "foryou.gate": "साइन इन करा आणि तुमच्या परिस्थितीनुसार शिफारसी मिळवा — शेतकरी, सरकारी कर्मचारी, डॉक्टर, विद्यार्थी, ज्येष्ठ नागरिक, कामगार किंवा व्यावसायिक.",
    "foryou.title": "तुमच्यासाठी योजना आणि लाभ",
    "foryou.iam": "मी आहे",
    "foryou.also": "सर्वांसाठी उपयुक्त",
    "centres.title": "मला कुठे जायचे आहे?",
    "centres.lede": "सेवा आणि भागानुसार कार्यालयांच्या यादीत शोधा. ही नमुना यादी आहे — जाण्यापूर्वी पत्ता आणि वेळ अधिकृत पोर्टलवर तपासा.",
    "centres.service": "सेवा",
    "centres.area": "भाग, जिल्हा किंवा राज्य",
    "centres.search": "केंद्र शोधा",
    "centres.any": "कोणतीही सेवा",
    "centres.none": "या शोधासाठी केंद्र सापडले नाही. दुसरा जिल्हा किंवा सेवा वापरून पाहा.",
    "centres.maps": "नकाशात उघडा",
    "centres.services": "सेवा",
    "privacy.link": "गोपनीयता आणि सुरक्षा",
    "auth.title": "तुमचे Samajh खाते",
    "auth.signin": "साइन इन",
    "auth.register": "खाते तयार करा",
    "auth.email": "ईमेल",
    "auth.password": "पासवर्ड",
    "auth.name": "तुमचे नाव",
    "auth.role": "मी आहे",
    "auth.area": "भाग / जिल्हा (केंद्र आणि शिफारशींसाठी)",
    "auth.phone": "फोन (पर्यायी)",
    "auth.consent": "मला समजते की Samajh फक्त मी निवडलेले थोडेच, एन्क्रिप्ट करून ठेवते, आणि मी कधीही खाते व डेटा हटवू शकतो/शकते.",
    "auth.note": "तुमचे स्कॅन अशा कीने एन्क्रिप्ट आहेत जी फक्त तुमचे खाते उघडू शकते. खाते पॅनेलमधून सर्व डेटा डाउनलोड किंवा हटवता येतो.",
    "account.title": "खाते आणि गोपनीयता",
    "account.signedOut": "तुम्ही पाहुणे म्हणून पाहत आहात. खाते तयार केल्याशिवाय काहीही जतन होत नाही.",
    "account.saveProfile": "प्रोफाइल जतन करा",
    "account.changePassword": "पासवर्ड बदला",
    "account.currentPassword": "सध्याचा पासवर्ड",
    "account.newPassword": "नवीन पासवर्ड (8+ अक्षरे)",
    "account.privacyTitle": "गोपनीयता आणि सुरक्षा",
    "account.export": "माझा डेटा डाउनलोड करा (JSON)",
    "account.logout": "साइन आउट",
    "account.delete": "खाते आणि सर्व डेटा हटवा",
    "account.deleteConfirm": "यामुळे तुमचे खाते, प्रत्येक स्कॅन, अर्ज आणि सूचना हटतील. हे पुन्हा मिळणार नाही. पुढे जायचे?",
    "alerts.title": "सूचना आणि इशारे",
    "alerts.empty": "सध्या कशाकडेही लक्ष देण्याची गरज नाही. तुमच्या स्कॅन व अर्जांच्या मुदती इथे दिसतील.",
    "alerts.add": "स्मरणपत्र लावा",
    "alerts.what": "कशाची आठवण करून द्यावी?",
    "alerts.when": "तारीख (YYYY-MM-DD)",
    "alerts.save": "स्मरणपत्र जतन करा",
    "alerts.dismiss": "झाले",
    "alerts.delete": "हटवा",
    "comfort.title": "आराम सेटिंग्ज",
    "comfort.size": "अक्षरांचा आकार",
    "comfort.contrast": "हाय कॉन्ट्रास्ट",
    "comfort.spacing": "वाचायला सोपी स्पेसिंग",
    "comfort.autospeak": "उत्तरे स्वतःहून वाचून दाखवा (टेक्स्ट टू स्पीच)",
    "comfort.ttsNote": "टेक्स्ट टू स्पीच तुमच्या डिव्हाइसचे आवाज वापरते. कोणत्याही उत्तरावर \"वाचून दाखवा\" दाबू शकता.",
    "btn.read": "वाचून दाखवा",
    "btn.stop": "वाचणे थांबवा",
    "btn.view": "उघडा",
    "btn.reread": "पुन्हा वाचा",
    "btn.download": "डाउनलोड",
    "btn.delete": "हटवा",
    "btn.pdf": "चेकलिस्ट PDF",
    "btn.track": "हे काम ट्रॅक करा",
    "status.started": "सुरू",
    "status.documents_gathered": "कागदपत्रे जमा",
    "status.submitted": "सादर",
    "status.under_review": "तपासणीत",
    "status.action_needed": "तुमच्याकडून कृती हवी",
    "status.approved": "मंजूर",
    "status.rejected": "नामंजूर",
    "status.completed": "पूर्ण",
    "sheet.compulsory": "बंधनकारक कागदपत्रे",
    "sheet.optional": "पर्यायी / अतिरिक्त कागदपत्रे",
    "sheet.costs": "येणारा खर्च",
    "sheet.where": "कुठे जायचे",
    "sheet.processing": "किती वेळ लागेल",
    "sheet.warnings": "इशारे — सावध राहा",
    "sheet.steps": "क्रमाने पायऱ्या",
    "sheet.verify": "काम करण्यापूर्वी अधिकृत पोर्टलवर नक्की तपासा.",
    "analysis.actions": "काय करायचे",
    "analysis.deadlines": "मुदती",
    "analysis.flags": "यांच्याकडे लक्ष द्या",
    "analysis.verdicts": "दोन स्पष्ट मते",
    "analysis.canIgnore": "हे बाजूला ठेवू शकता:",
    "analysis.needsAttention": "याकडे लक्ष द्या:",
    "analysis.pro": "तज्ज्ञ मदत करू शकतो:",
    "analysis.noPro": "तज्ज्ञाची गरज नाही:",
    "analysis.facts": "मुख्य तथ्ये",
    "analysis.saved": "एन्क्रिप्टेड प्रत तुमच्या व्हॉल्टमध्ये जतन झाली.",
    "analysis.overdue": "मुदत संपली",
    "analysis.actby": "या तारखेपर्यंत",
    "analysis.actsoon": "लवकर करा",
    "analysis.ignore": "दुर्लक्ष करू शकता",
    "analysis.onfile": "फाइलवर",
    "urgency.now": "आत्ता करा",
    "urgency.soon": "लवकर करा",
    "urgency.later": "संधी मिळेल तेव्हा",
    "days.past": "दिवस आधी",
    "days.today": "आज",
    "days.left": "दिवस शिल्लक",
    "vault.empty": "अजून स्कॅन जतन केलेले नाही. अपलोड करण्यापूर्वी \"हा स्कॅन ठेवा\" निवडा.",
    "vault.expires": "स्वतःहून हटेल",
    "err.reach": "सेवेपर्यंत पोहोचलो नाही. कनेक्शन तपासा आणि पुन्हा प्रयत्न करा.",
    "err.generic": "काहीतरी चुकले. पुन्हा प्रयत्न करा.",
    "toast.saved": "जतन झाले.",
    "toast.deleted": "हटवले.",
    "foryou.benefits": "तुम्हाला काय मिळेल",
    "foryou.eligibility": "कोण अर्ज करू शकतो",
    "foryou.documents": "तयार ठेवायची कागदपत्रे",
    "foryou.costs": "अतिरिक्त खर्च",
    "foryou.where": "कुठे जायचे",
    "foryou.forms": "Samajh मधील फॉर्म",
    "foryou.steps": "क्रमाने पायऱ्या",
    "foryou.warnings": "इशारे",
    "foryou.official": "अधिकृत पोर्टल",
    "roles.citizen": "सामान्य नागरिक",
    "roles.farmer": "शेतकरी",
    "roles.govt_employee": "सरकारी कर्मचारी",
    "roles.doctor": "डॉक्टर",
    "roles.student": "विद्यार्थी",
    "roles.senior_citizen": "ज्येष्ठ नागरिक",
    "roles.entrepreneur": "व्यावसायिक / उद्योजक",
    "roles.worker": "कामगार (असंघटित)",
  },
};

function t(key) {
  return (I18N[state.lang] && I18N[state.lang][key]) || I18N.en[key] || key;
}

function applyI18n() {
  document.documentElement.lang = state.lang;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
  });
}

/* ============================== utilities ============================== */

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

const MAX_LEN = 400;

function clip(s, n = MAX_LEN) {
  s = String(s ?? "");
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => { el.hidden = true; }, 3200);
}

async function api(path, options = {}) {
  const opts = { credentials: "same-origin", ...options };
  if (opts.body && typeof opts.body === "object" && !(opts.body instanceof FormData)) {
    opts.headers = { "Content-Type": "application/json", ...(opts.headers || {}) };
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON (e.g. PDF) */ }
  if (!res.ok) {
    const msg = (data && (data.detail || data.error)) || t("err.generic");
    const err = new Error(typeof msg === "string" ? msg : t("err.generic"));
    err.status = res.status;
    throw err;
  }
  return data;
}

async function downloadPdf(path, options = {}) {
  try {
    const res = await fetch(path, { credentials: "same-origin", ...options });
    if (!res.ok) {
      let msg = t("err.generic");
      try { const d = await res.json(); msg = d.detail || d.error || msg; } catch { /* ignore */ }
      toast(msg);
      return;
    }
    const blob = await res.blob();
    const disposition = res.headers.get("content-disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    const name = match ? match[1] : "samajh.pdf";
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  } catch {
    toast(t("err.reach"));
  }
}

function fmtDate(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso.length <= 10 ? iso + "T00:00:00" : iso)
      .toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  } catch { return iso; }
}

function fmtBytes(n) {
  if (!n) return "0 KB";
  return n > 1024 * 1024 ? (n / 1024 / 1024).toFixed(1) + " MB" : Math.round(n / 1024) + " KB";
}

/* ============================== text to speech ============================== */

let currentUtterance = null;

function ttsSupported() {
  return "speechSynthesis" in window;
}

function speak(text, lang = state.lang) {
  if (!ttsSupported() || !text) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(clip(text, 1200));
  u.lang = state.locales[lang] || "en-IN";
  const voices = window.speechSynthesis.getVoices();
  const match = voices.find((v) => v.lang === u.lang) || voices.find((v) => v.lang.startsWith((u.lang || "").slice(0, 2)));
  if (match) u.voice = match;
  u.rate = 0.95;
  currentUtterance = u;
  window.speechSynthesis.speak(u);
}

function stopSpeaking() {
  if (ttsSupported()) window.speechSynthesis.cancel();
  currentUtterance = null;
}

function speakButton(label, text) {
  return `<button class="link-btn speak-btn" type="button" data-speak="${esc(clip(text, 1200))}">${esc(label || t("btn.read"))}</button>`;
}

/* ============================== tabs ============================== */

const TABS = {
  doc: "panel-doc",
  forms: "panel-forms",
  track: "panel-track",
  foryou: "panel-foryou",
  centres: "panel-centres",
};

function selectTab(which) {
  Object.entries(TABS).forEach(([key, panelId]) => {
    const tab = $("tab-" + key);
    const panel = $(panelId);
    const active = key === which;
    tab.classList.toggle("is-active", active);
    tab.setAttribute("aria-selected", String(active));
    panel.classList.toggle("is-active", active);
    panel.hidden = !active;
  });
  if (which === "track") refreshTracker();
  if (which === "foryou") refreshForYou();
  if (which === "centres") loadCentres();
  if (which === "doc") refreshVault();
}

Object.keys(TABS).forEach((key) => {
  $("tab-" + key).addEventListener("click", () => selectTab(key));
});

/* ============================== language ============================== */

async function initLanguages() {
  try {
    const health = await api("/api/health");
    if (health.langs) state.langs = health.langs;
    if (health.roles) state.roles = health.roles;
  } catch { /* defaults stand */ }
  state.roles = state.roles || {
    citizen: "General citizen", farmer: "Farmer", govt_employee: "Government service employee",
    doctor: "Doctor", student: "Student", senior_citizen: "Senior citizen",
    entrepreneur: "Business owner / entrepreneur", worker: "Worker (unorganised sector)",
  };
  const select = $("lang-select");
  select.innerHTML = "";
  Object.entries(state.langs).forEach(([code, name]) => {
    const opt = document.createElement("option");
    opt.value = code;
    opt.textContent = name;
    if (code === state.lang) opt.selected = true;
    select.appendChild(opt);
  });
  select.addEventListener("change", () => {
    state.lang = select.value;
    localStorage.setItem("samajh_lang", state.lang);
    applyI18n();
    refreshDynamicTexts();
  });
  populateRoleSelects();
}

function populateRoleSelects() {
  ["reg-role", "pf-role", "role-select"].forEach((id) => {
    const el = $(id);
    if (!el) return;
    const current = el.value;
    el.innerHTML = "";
    Object.entries(state.roles).forEach(([code, name]) => {
      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = name;
      el.appendChild(opt);
    });
    if (current) el.value = current;
  });
  if (state.user) {
    $("reg-role").value = state.user.role || "citizen";
    $("pf-role").value = state.user.role || "citizen";
    $("role-select").value = state.user.role || "citizen";
  }
}

function refreshDynamicTexts() {
  if (state.lastAnalysis) renderAnalysis(state.lastAnalysis);
  if (state.lastSheet) {
    const holder = document.querySelector(".chat-sheet-live");
    if (holder && holder.dataset.sheet) {
      try { holder.innerHTML = renderFormSheet(JSON.parse(holder.dataset.sheet)); } catch { /* ignore */ }
    }
  }
  refreshVault();
  refreshTracker();
  refreshForYou();
  if (!$("alerts-overlay").hidden) refreshAlerts();
}

/* ============================== comfort ============================== */

function applyComfort() {
  document.documentElement.style.fontSize = state.comfort.size + "%";
  document.body.classList.toggle("high-contrast", state.comfort.contrast);
  document.body.classList.toggle("easy-reading", state.comfort.spacing);
  $("comfort-size").value = state.comfort.size;
  $("comfort-contrast").checked = state.comfort.contrast;
  $("comfort-spacing").checked = state.comfort.spacing;
  $("comfort-autospeak").checked = state.comfort.autospeak;
}

function bindComfort() {
  $("comfort-size").addEventListener("input", (e) => {
    state.comfort.size = Number(e.target.value);
    localStorage.setItem("samajh_size", state.comfort.size);
    applyComfort();
  });
  $("comfort-contrast").addEventListener("change", (e) => {
    state.comfort.contrast = e.target.checked;
    localStorage.setItem("samajh_contrast", state.comfort.contrast ? "1" : "0");
    applyComfort();
  });
  $("comfort-spacing").addEventListener("change", (e) => {
    state.comfort.spacing = e.target.checked;
    localStorage.setItem("samajh_spacing", state.comfort.spacing ? "1" : "0");
    applyComfort();
  });
  $("comfort-autospeak").addEventListener("change", (e) => {
    state.comfort.autospeak = e.target.checked;
    localStorage.setItem("samajh_autospeak", state.comfort.autospeak ? "1" : "0");
  });
  $("comfort-btn").addEventListener("click", () => openOverlay("comfort-overlay"));
  $("comfort-close").addEventListener("click", () => closeOverlay("comfort-overlay"));
}

/* ============================== overlays ============================== */

function openOverlay(id) {
  document.querySelectorAll(".overlay").forEach((o) => { o.hidden = true; });
  $(id).hidden = false;
  document.body.classList.add("overlay-open");
}

function closeOverlay(id) {
  $(id).hidden = true;
  document.body.classList.remove("overlay-open");
}

document.querySelectorAll(".overlay").forEach((overlay) => {
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) { overlay.hidden = true; document.body.classList.remove("overlay-open"); }
  });
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    document.querySelectorAll(".overlay").forEach((o) => { o.hidden = true; });
    document.body.classList.remove("overlay-open");
  }
});

/* ============================== auth ============================== */

function showAuthError(message) {
  const el = $("auth-error");
  el.textContent = message;
  el.hidden = false;
}

function clearAuthError() { $("auth-error").hidden = true; }

function openAuth(tab = "login") {
  clearAuthError();
  const login = tab === "login";
  $("auth-tab-login").classList.toggle("is-active", login);
  $("auth-tab-register").classList.toggle("is-active", !login);
  $("login-form").hidden = !login;
  $("register-form").hidden = login;
  openOverlay("auth-overlay");
}

function setUser(user) {
  state.user = user;
  const signedIn = Boolean(user);
  $("account-label").textContent = signedIn ? (user.name || user.email) : t("nav.signin");
  $("track-gate").hidden = signedIn;
  $("track-body").hidden = !signedIn;
  $("foryou-gate").hidden = signedIn;
  $("foryou-body").hidden = !signedIn;
  $("account-signed-out").hidden = signedIn;
  $("account-signed-in").hidden = !signedIn;
  $("save-toggle-wrap").hidden = !signedIn;
  $("vault").hidden = !signedIn;
  $("alerts-btn").hidden = !signedIn;
  if (signedIn) {
    $("account-name").textContent = user.name || "";
    $("account-email").textContent = user.email || "";
    $("pf-name").value = user.name || "";
    $("pf-area").value = user.area || "";
    $("pf-phone").value = user.phone || "";
    $("pf-role").value = user.role || "citizen";
    $("role-select").value = user.role || "citizen";
    if (user.lang && state.langs[user.lang] && user.lang !== state.lang) {
      state.lang = user.lang;
      localStorage.setItem("samajh_lang", state.lang);
      $("lang-select").value = state.lang;
      applyI18n();
    }
    refreshVault();
    refreshAlertsBadge();
  } else {
    $("alerts-badge").hidden = true;
    $("vault-list").innerHTML = "";
  }
}

async function loadMe() {
  try {
    const user = await api("/api/auth/me");
    setUser(user);
    if (user.area) $("centre-area").value = user.area;
  } catch {
    setUser(null);
  }
}

$("account-btn").addEventListener("click", () => {
  if (state.user) openOverlay("account-overlay");
  else openAuth("login");
});

$("auth-tab-login").addEventListener("click", () => openAuth("login"));
$("auth-tab-register").addEventListener("click", () => openAuth("register"));
$("auth-close").addEventListener("click", () => closeOverlay("auth-overlay"));

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  clearAuthError();
  try {
    const data = await api("/api/auth/login", {
      method: "POST",
      body: { email: $("login-email").value.trim(), password: $("login-password").value },
    });
    setUser(data.user);
    closeOverlay("auth-overlay");
    toast(t("toast.saved"));
  } catch (err) {
    showAuthError(err.message);
  }
});

$("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  clearAuthError();
  try {
    const data = await api("/api/auth/register", {
      method: "POST",
      body: {
        name: $("reg-name").value.trim(),
        email: $("reg-email").value.trim(),
        password: $("reg-password").value,
        role: $("reg-role").value,
        lang: state.lang,
        area: $("reg-area").value.trim(),
        consent: $("reg-consent").checked,
      },
    });
    setUser(data.user);
    closeOverlay("auth-overlay");
  } catch (err) {
    showAuthError(err.message);
  }
});

$("track-signin").addEventListener("click", () => openAuth("login"));
$("foryou-signin").addEventListener("click", () => openAuth("login"));
$("account-signin").addEventListener("click", () => { closeOverlay("account-overlay"); openAuth("login"); });
$("account-close").addEventListener("click", () => closeOverlay("account-overlay"));

$("profile-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const user = await api("/api/auth/me", {
      method: "PATCH",
      body: {
        name: $("pf-name").value.trim(),
        role: $("pf-role").value,
        area: $("pf-area").value.trim(),
        phone: $("pf-phone").value.trim(),
      },
    });
    setUser(user);
    toast(t("toast.saved"));
  } catch (err) { toast(err.message); }
});

$("password-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/auth/password", {
      method: "POST",
      body: { current_password: $("pw-current").value, new_password: $("pw-new").value },
    });
    $("pw-current").value = "";
    $("pw-new").value = "";
    toast(t("toast.saved"));
  } catch (err) { toast(err.message); }
});

$("logout-btn").addEventListener("click", async () => {
  try { await api("/api/auth/logout", { method: "POST" }); } catch { /* ignore */ }
  setUser(null);
  closeOverlay("account-overlay");
});

$("export-btn").addEventListener("click", () => {
  window.open("/api/auth/export", "_blank");
});

$("delete-account-btn").addEventListener("click", async () => {
  if (!window.confirm(t("account.deleteConfirm"))) return;
  try {
    await api("/api/auth/me", { method: "DELETE" });
    setUser(null);
    closeOverlay("account-overlay");
    toast(t("toast.deleted"));
  } catch (err) { toast(err.message); }
});

$("footer-privacy").addEventListener("click", async () => {
  try {
    const p = await api("/api/privacy");
    $("privacy-list").innerHTML = (p.notes || []).map((n) => `<li>${esc(n)}</li>`).join("");
  } catch { /* ignore */ }
  openOverlay("account-overlay");
});

async function loadPrivacyNote() {
  try {
    const p = await api("/api/privacy");
    $("privacy-list").innerHTML = (p.notes || []).map((n) => `<li>${esc(n)}</li>`).join("");
  } catch { /* ignore */ }
}

/* ============================== alerts ============================== */

async function refreshAlertsBadge() {
  if (!state.user) return;
  try {
    const data = await api("/api/alerts");
    state.alerts = data.alerts || [];
    const badge = $("alerts-badge");
    const active = state.alerts.filter((a) => !a.read).length;
    badge.textContent = active > 99 ? "99+" : String(active);
    badge.hidden = active === 0;
  } catch { /* ignore */ }
}

function alertRow(a, i) {
  const days = a.days_left;
  let when = "";
  if (days !== undefined && days !== null) {
    when = days < 0 ? `${Math.abs(days)} ${t("days.past")}` : days === 0 ? t("days.today") : `${days} ${t("days.left")}`;
  } else if (a.due_date) {
    when = fmtDate(a.due_date);
  }
  const manual = a.source === "manual";
  return `
    <div class="alert-item ${a.kind === "warning" ? "warn" : ""} ${a.read ? "read" : ""}">
      <p class="alert-title">${esc(clip(a.title, 160))}</p>
      ${a.body ? `<p class="alert-body">${esc(clip(a.body, 300))}</p>` : ""}
      ${when ? `<p class="alert-when">${esc(when)}</p>` : ""}
      ${manual ? `<div class="alert-actions">
        <button class="link-btn" type="button" data-alert-done="${a.alert_id}">${esc(t("alerts.dismiss"))}</button>
        <button class="link-btn danger" type="button" data-alert-del="${a.alert_id}">${esc(t("alerts.delete"))}</button>
      </div>` : ""}
    </div>`;
}

async function refreshAlerts() {
  if (!state.user) {
    $("alerts-list").innerHTML = `<p class="muted">${esc(t("track.gate"))}</p>`;
    $("alert-form").hidden = true;
    return;
  }
  $("alert-form").hidden = false;
  try {
    const data = await api("/api/alerts");
    state.alerts = data.alerts || [];
    const badge = $("alerts-badge");
    const active = state.alerts.filter((a) => !a.read).length;
    badge.textContent = active > 99 ? "99+" : String(active);
    badge.hidden = active === 0;
    $("alerts-list").innerHTML = state.alerts.length
      ? state.alerts.map(alertRow).join("")
      : `<p class="muted">${esc(t("alerts.empty"))}</p>`;
  } catch (err) {
    $("alerts-list").innerHTML = `<p class="muted">${esc(err.message)}</p>`;
  }
}

$("alerts-btn").addEventListener("click", () => { openOverlay("alerts-overlay"); refreshAlerts(); });
$("alerts-close").addEventListener("click", () => closeOverlay("alerts-overlay"));

$("alerts-list").addEventListener("click", async (e) => {
  const done = e.target.closest("[data-alert-done]");
  const del = e.target.closest("[data-alert-del]");
  try {
    if (done) {
      await api(`/api/alerts/${done.dataset.alertDone}`, { method: "PATCH", body: { read: true } });
      refreshAlerts();
    } else if (del) {
      await api(`/api/alerts/${del.dataset.alertDel}`, { method: "DELETE" });
      refreshAlerts();
    }
  } catch (err) { toast(err.message); }
});

$("alert-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/alerts", {
      method: "POST",
      body: {
        title: $("alert-title").value.trim(),
        due_date: $("alert-date").value || null,
        kind: "reminder",
      },
    });
    $("alert-title").value = "";
    $("alert-date").value = "";
    refreshAlerts();
    toast(t("toast.saved"));
  } catch (err) { toast(err.message); }
});

/* ============================== document reading ============================== */

const tray = $("drop-tray");
const fileInput = $("file-input");

function showDocError(text) {
  const el = $("doc-error");
  el.textContent = text;
  el.hidden = false;
}
function clearDocError() { $("doc-error").hidden = true; }

function acceptFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    showDocError("That is not an image file. A photo or scan of the document is needed (JPG, PNG or WebP).");
    return;
  }
  if (file.size > 8 * 1024 * 1024) {
    showDocError("That file is over 8 MB. A smaller photo works just as well.");
    return;
  }
  clearDocError();
  state.imageFile = file;
  const url = URL.createObjectURL(file);
  $("paper-img").src = url;
  $("paper-img").dataset.scanId = "";
  tray.hidden = true;
  $("paper-frame").hidden = false;
  analyze(file);
}

tray.addEventListener("click", () => fileInput.click());
tray.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); fileInput.click(); }
});
fileInput.addEventListener("change", () => acceptFile(fileInput.files[0]));

["dragover", "dragenter"].forEach((ev) =>
  tray.addEventListener(ev, (e) => { e.preventDefault(); tray.classList.add("is-dragover"); }));
["dragleave", "drop"].forEach((ev) =>
  tray.addEventListener(ev, (e) => { e.preventDefault(); tray.classList.remove("is-dragover"); }));
tray.addEventListener("drop", (e) => acceptFile(e.dataTransfer.files[0]));

document.addEventListener("paste", (e) => {
  if (!e.clipboardData) return;
  const item = [...(e.clipboardData.items || [])].find((i) => i.type.startsWith("image/"));
  if (item) { selectTab("doc"); acceptFile(item.getAsFile()); }
});

$("paper-change").addEventListener("click", () => fileInput.click());

async function analyze(file) {
  if (state.busy) return;
  state.busy = true;
  $("doc-loading").hidden = false;
  $("doc-result").hidden = true;
  clearDocError();
  try {
    const fd = new FormData();
    fd.append("image", file, file.name || "document.jpg");
    fd.append("lang", state.lang);
    const saveWanted = state.user && $("save-toggle").checked;
    fd.append("save", saveWanted ? "1" : "0");
    const data = await api("/api/analyze", { method: "POST", body: fd });
    state.lastAnalysis = data;
    renderAnalysis(data);
    if (data.saved_scan_id) {
      toast(t("analysis.saved"));
      refreshVault();
      $("paper-img").dataset.scanId = String(data.saved_scan_id);
    }
  } catch (err) {
    showDocError(err.message);
  } finally {
    $("doc-loading").hidden = true;
    state.busy = false;
  }
}

function stampFor(r) {
  const soon = (r.deadlines || []).some((d) => d.days_left !== null && d.days_left <= 14 && d.days_left >= 0);
  const overdue = (r.deadlines || []).some((d) => d.days_left !== null && d.days_left < 0);
  const urgent = (r.actions || []).some((a) => a.urgency === "now");
  const nextDate = (r.deadlines || []).filter((d) => d.date_iso).map((d) => d.date_iso)[0];
  if (overdue) return { text: t("analysis.overdue"), cls: "" };
  if (urgent || soon) return { text: nextDate ? t("analysis.actby") + " " + fmtDate(nextDate).toUpperCase() : t("analysis.actsoon"), cls: "" };
  if (r.can_ignore && r.can_ignore.value) return { text: t("analysis.ignore"), cls: "green" };
  return { text: t("analysis.onfile"), cls: "green" };
}

function analysisSpeakText(r) {
  return [
    r.document_type, r.issuer, r.summary, r.explanation,
    ...(r.actions || []).map((a) => a.text),
    ...(r.deadlines || []).map((d) => `${d.what} ${d.date_iso || ""}`),
    ...(r.red_flags || []),
  ].filter(Boolean).join(". ");
}

function renderAnalysis(r) {
  const stamp = stampFor(r);
  const facts = [...(r.key_facts || []), ...(r.amounts || [])]
    .slice(0, 8)
    .map((f) => `<div class="fact-cell"><p class="fact-label">${esc(clip(f.label, 60))}</p><p class="fact-value">${esc(clip(f.value, 80))}</p></div>`)
    .join("");

  const actions = (r.actions || []).map((a, i) =>
    `<div class="action-row"><span class="action-num">${i + 1}</span><p class="action-text">${esc(clip(a.text, 300))}</p>
     <span class="action-when ${esc(a.urgency)}">${esc(t("urgency." + a.urgency))}</span></div>`).join("");

  const deadlines = (r.deadlines || []).map((d) => {
    let left = "";
    if (d.days_left !== null && d.days_left !== undefined) {
      if (d.days_left < 0) left = Math.abs(d.days_left) + " " + t("days.past");
      else if (d.days_left === 0) left = t("days.today");
      else left = d.days_left + " " + t("days.left");
    }
    const cls = (d.days_left !== null && d.days_left <= 7) ? (d.days_left < 0 ? "overdue" : "soon") : "";
    return `<div class="deadline-row"><span class="deadline-date">${esc(fmtDate(d.date_iso))}</span>
      <span class="deadline-what">${esc(clip(d.what, 200))}</span>
      <span class="deadline-left ${cls}">${esc(left)}</span></div>`;
  }).join("");

  const redflags = (r.red_flags || []).map((x) => `<p class="redflag">${esc(clip(x, 300))}</p>`).join("");

  $("doc-result").innerHTML = `
    <div class="stamp ${stamp.cls}">${esc(stamp.text)}</div>
    <h2 class="doc-type">${esc(r.document_type || "Document")}</h2>
    <p class="doc-issuer">${esc(r.issuer || "")}</p>
    <p class="doc-summary">${esc(r.summary)}</p>
    <p class="doc-explanation">${esc(r.explanation)}</p>
    ${facts ? `<div class="fact-strip">${facts}</div>` : ""}
    ${actions ? `<div class="actions"><p class="section-label">${esc(t("analysis.actions"))}</p>${actions}</div>` : ""}
    ${deadlines ? `<div class="deadlines"><p class="section-label">${esc(t("analysis.deadlines"))}</p>${deadlines}</div>` : ""}
    ${redflags ? `<div class="redflags"><p class="section-label">${esc(t("analysis.flags"))}</p>${redflags}</div>` : ""}
    <div class="verdict">
      <p class="section-label">${esc(t("analysis.verdicts"))}</p>
      <p><strong class="${r.can_ignore?.value ? "flag-no" : "flag-yes"}">${esc(r.can_ignore?.value ? t("analysis.canIgnore") : t("analysis.needsAttention"))}</strong> ${esc(r.can_ignore?.reason || "")}</p>
      <p><strong class="${r.needs_professional?.value ? "flag-yes" : "flag-no"}">${esc(r.needs_professional?.value ? t("analysis.pro") : t("analysis.noPro"))}</strong> ${esc(r.needs_professional?.reason || "")}</p>
    </div>
    <div class="result-tools">
      ${speakButton(t("btn.read"), analysisSpeakText(r))}
      <button class="link-btn" id="analysis-pdf" type="button">${esc(t("doc.pdf"))}</button>
    </div>
    ${metaBlock(r.trace)}
  `;
  $("doc-result").hidden = false;
  $("analysis-pdf").addEventListener("click", downloadAnalysisPdf);
  if (state.comfort.autospeak) speak(analysisSpeakText(r));
}

function metaBlock(trace) {
  if (!trace) return "";
  const lines = [];
  lines.push("model: " + (trace.model || "—"));
  lines.push("key slot: " + (trace.key_slot !== undefined ? trace.key_slot : "—"));
  lines.push("latency: " + (trace.latency_ms || "—") + " ms");
  return `<details class="answer-meta"><summary>How this was answered</summary><pre>${esc(lines.join("\n"))}</pre></details>`;
}

function downloadAnalysisPdf() {
  const r = state.lastAnalysis;
  if (!r) return;
  const sections = [
    { heading: t("analysis.actions"), items: (r.actions || []).map((a) => `[${t("urgency." + a.urgency)}] ${a.text}`) },
    { heading: t("analysis.deadlines"), items: (r.deadlines || []).map((d) => `${fmtDate(d.date_iso)} — ${d.what}`) },
    { heading: t("analysis.flags"), items: r.red_flags || [] },
    { heading: t("analysis.facts"), items: [...(r.key_facts || []), ...(r.amounts || [])].map((f) => `${f.label}: ${f.value}`) },
  ].filter((s) => s.items && s.items.length);
  downloadPdf("/api/pdf/checklist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title: r.document_type || "Document reading",
      subtitle: r.summary || "",
      sections,
      lang: state.lang,
    }),
  });
}

/* ---------- vault ---------- */

async function refreshVault() {
  if (!state.user) return;
  try {
    const data = await api("/api/scans");
    const list = $("vault-list");
    if (!data.scans.length) {
      list.innerHTML = `<p class="muted small">${esc(t("vault.empty"))}</p>`;
      return;
    }
    list.innerHTML = data.scans.map((s) => `
      <div class="vault-item" title="${esc(s.doc_type || "")}">
        <div class="vault-info">
          <p class="vault-label">${esc(clip(s.label, 60))}</p>
          <p class="muted small">${esc(fmtDate(s.created_at))} · ${esc(fmtBytes(s.size))}</p>
        </div>
        <div class="vault-actions">
          <button class="link-btn" type="button" data-scan-view="${s.id}">${esc(t("btn.view"))}</button>
          <button class="link-btn" type="button" data-scan-analyze="${s.id}">${esc(t("btn.reread"))}</button>
          <button class="link-btn" type="button" data-scan-download="${s.id}">${esc(t("btn.download"))}</button>
          <button class="link-btn danger" type="button" data-scan-del="${s.id}">${esc(t("btn.delete"))}</button>
        </div>
      </div>`).join("");
  } catch { /* ignore */ }
}

$("vault-list").addEventListener("click", async (e) => {
  const view = e.target.closest("[data-scan-view]");
  const reanalyze = e.target.closest("[data-scan-analyze]");
  const download = e.target.closest("[data-scan-download]");
  const del = e.target.closest("[data-scan-del]");
  try {
    if (view) {
      const id = view.dataset.scanView;
      const res = await fetch(`/api/scans/${id}/image`, { credentials: "same-origin" });
      if (!res.ok) throw new Error(t("err.generic"));
      const blob = await res.blob();
      $("paper-img").src = URL.createObjectURL(blob);
      $("paper-img").dataset.scanId = id;
      tray.hidden = true;
      $("paper-frame").hidden = false;
      selectTab("doc");
    } else if (reanalyze) {
      const id = reanalyze.dataset.scanAnalyze;
      selectTab("doc");
      $("doc-loading").hidden = false;
      $("doc-result").hidden = true;
      const fd = new FormData();
      fd.append("lang", state.lang);
      const data = await api(`/api/scans/${id}/analyze`, { method: "POST", body: fd });
      state.lastAnalysis = data;
      renderAnalysis(data);
      const res = await fetch(`/api/scans/${id}/image`, { credentials: "same-origin" });
      if (res.ok) {
        $("paper-img").src = URL.createObjectURL(await res.blob());
        $("paper-img").dataset.scanId = id;
        tray.hidden = true;
        $("paper-frame").hidden = false;
      }
    } else if (download) {
      window.open(`/api/scans/${download.dataset.scanDownload}/download`, "_blank");
    } else if (del) {
      await api(`/api/scans/${del.dataset.scanDel}`, { method: "DELETE" });
      toast(t("toast.deleted"));
      refreshVault();
    }
  } catch (err) {
    toast(err.message);
  } finally {
    $("doc-loading").hidden = true;
  }
});

$("vault-delete-all").addEventListener("click", async () => {
  if (!window.confirm(t("account.deleteConfirm"))) return;
  try {
    await api("/api/scans", { method: "DELETE" });
    toast(t("toast.deleted"));
    refreshVault();
  } catch (err) { toast(err.message); }
});

$("paper-save").addEventListener("click", async () => {
  if (!state.imageFile) return;
  try {
    const fd = new FormData();
    fd.append("image", state.imageFile, state.imageFile.name || "scan.jpg");
    fd.append("lang", state.lang);
    const data = await api("/api/scans", { method: "POST", body: fd });
    $("paper-img").dataset.scanId = String(data.scan.id);
    toast(t("analysis.saved"));
    refreshVault();
  } catch (err) { toast(err.message); }
});

$("paper-pdf").addEventListener("click", () => {
  if (state.lastAnalysis) downloadAnalysisPdf();
});

/* ============================== form chat ============================== */

const transcript = $("transcript");

function addLine(speaker, html, isHtml = false) {
  const row = document.createElement("div");
  row.className = "transcript-row" + (speaker === "YOU" ? " you" : "");
  const who = document.createElement("span");
  who.className = "speaker";
  who.textContent = speaker;
  const body = document.createElement("div");
  body.className = "transcript-text";
  if (isHtml) body.innerHTML = html; else body.textContent = html;
  transcript.appendChild(row);
  row.appendChild(who);
  row.appendChild(body);
  row.scrollIntoView({ behavior: "smooth", block: "end" });
  return body;
}

function listBlock(label, items, box) {
  if (!items || !items.length) return "";
  const lis = items.map((d) => box
    ? `<li><label class="doc-check"><input type="checkbox" /><span>${esc(clip(d, 250))}</span></label></li>`
    : `<li><span>${esc(clip(d, 400))}</span></li>`).join("");
  return `<div class="sheet-block"><p class="section-label">${esc(label)}</p><ul class="sheet-checklist ${box ? "" : "plain"}">${lis}</ul></div>`;
}

function renderFormSheet(sheet) {
  const modeText = { home: "CAN BE DONE AT HOME", partly_home: "PARTLY AT HOME", in_person: "IN PERSON ONLY" }[sheet.mode] || sheet.mode;
  const cls = sheet.mode === "in_person" ? "red" : "";
  const steps = (sheet.steps || []).map((s, i) =>
    `<div class="sheet-step"><span class="sheet-step-num">${i + 1}</span><p>${esc(clip(s, 400))}</p></div>`).join("");
  const costs = (sheet.costs || []).length
    ? `<ul class="sheet-checklist plain">${sheet.costs.map((c) => `<li><span>${esc(clip(c.label, 120))}: ${esc(clip(c.value, 200))}</span></li>`).join("")}</ul>`
    : "";
  const warnings = (sheet.warnings || []).map((x) => `<p class="redflag">${esc(clip(x, 300))}</p>`).join("");
  const speakText = [
    sheet.form_name, sheet.mode_reason,
    ...(sheet.compulsory_documents || []),
    ...(sheet.steps || []),
    ...(sheet.warnings || []),
  ].filter(Boolean).join(". ");
  const formId = sheet.form_id || "";
  return `
    <div class="form-sheet">
      <div class="sheet-stamp ${cls}">${esc(modeText)}</div>
      <h2 class="sheet-title">${esc(sheet.form_name)}</h2>
      <p class="sheet-mode-reason">${esc(clip(sheet.mode_reason, 400))}</p>
      ${listBlock(t("sheet.compulsory"), sheet.compulsory_documents?.length ? sheet.compulsory_documents : sheet.documents, true)}
      ${listBlock(t("sheet.optional"), [...(sheet.optional_documents || [])], false)}
      ${costs ? `<div class="sheet-block"><p class="section-label">${esc(t("sheet.costs"))}</p>${costs}</div>` : ""}
      ${sheet.where_to_go ? `<div class="sheet-block"><p class="section-label">${esc(t("sheet.where"))}</p><p>${esc(clip(sheet.where_to_go, 300))}</p></div>` : ""}
      ${sheet.processing_time ? `<div class="sheet-block"><p class="section-label">${esc(t("sheet.processing"))}</p><p>${esc(clip(sheet.processing_time, 200))}</p></div>` : ""}
      ${warnings ? `<div class="sheet-block redflags"><p class="section-label">${esc(t("sheet.warnings"))}</p>${warnings}</div>` : ""}
      ${steps ? `<div class="sheet-steps"><p class="section-label">${esc(t("sheet.steps"))}</p>${steps}</div>` : ""}
      ${sheet.extra_info ? `<p class="sheet-notes">${esc(clip(sheet.extra_info, 400))}</p>` : ""}
      ${sheet.notes ? `<p class="sheet-notes">${esc(clip(sheet.notes, 300))}</p>` : ""}
      ${sheet.official_url ? `<a class="sheet-link" href="${esc(sheet.official_url)}" target="_blank" rel="noopener noreferrer">${esc(sheet.official_url)}</a>` : ""}
      <p class="sheet-verify">${esc(t("sheet.verify"))}</p>
      <div class="result-tools">
        ${speakButton(t("btn.read"), speakText)}
        ${formId ? `<button class="link-btn" type="button" data-pdf-form="${esc(formId)}">${esc(t("btn.pdf"))}</button>` : ""}
        ${state.user && formId ? `<button class="link-btn" type="button" data-track-form="${esc(formId)}" data-track-name="${esc(sheet.form_name)}">${esc(t("btn.track"))}</button>` : ""}
      </div>
      ${metaBlock(sheet.trace)}
    </div>`;
}

async function ask(message) {
  if (state.busy) return;
  state.busy = true;
  addLine("YOU", message);
  $("chat-loading").hidden = false;
  $("chat-send").disabled = true;
  try {
    const data = await api("/api/chat", { method: "POST", body: { message, lang: state.lang } });
    if (!data) return;
    if (data.type === "form_sheet") {
      const toolCalls = (data.trace && data.trace.tool_calls) || [];
      const tool = toolCalls.find((c) => c.tool === "get_form_requirements" && c.args && c.args.form_id);
      data.form_id = tool ? tool.args.form_id : "";
      state.lastSheet = data;
      const holder = addLine("SAMAJH", "", true);
      holder.classList.add("chat-sheet-live");
      holder.dataset.sheet = JSON.stringify(data);
      holder.innerHTML = renderFormSheet(data);
      if (state.comfort.autospeak) speak(data.form_name + ". " + (data.mode_reason || ""));
    } else {
      const text = data.text || "";
      const holder = addLine("SAMAJH", "", true);
      holder.innerHTML = `<p>${esc(text)}</p><div class="result-tools">${speakButton(t("btn.read"), text)}</div>`;
      if (state.comfort.autospeak) speak(text);
    }
  } catch (err) {
    addLine("SAMAJH", err.message);
  } finally {
    $("chat-loading").hidden = true;
    $("chat-send").disabled = false;
    state.busy = false;
  }
}

$("chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const value = $("chat-input").value.trim();
  if (!value) return;
  $("chat-input").value = "";
  ask(value);
});

document.addEventListener("click", (e) => {
  const speakBtn = e.target.closest("[data-speak]");
  if (speakBtn) {
    if (currentUtterance && window.speechSynthesis.speaking) {
      stopSpeaking();
      speakBtn.textContent = t("btn.read");
    } else {
      speak(speakBtn.dataset.speak);
      speakBtn.textContent = t("btn.stop");
      setTimeout(() => { speakBtn.textContent = t("btn.read"); }, 1500);
    }
    return;
  }
  const pdfForm = e.target.closest("[data-pdf-form]");
  if (pdfForm) {
    downloadPdf(`/api/pdf/form/${encodeURIComponent(pdfForm.dataset.pdfForm)}?lang=${state.lang}`);
    return;
  }
  const trackForm = e.target.closest("[data-track-form]");
  if (trackForm) {
    selectTab("track");
    $("app-form").hidden = false;
    $("app-form-select").value = trackForm.dataset.trackForm;
    $("app-name").value = "";
  }
});

async function loadSuggestions() {
  try {
    const data = await api("/api/forms");
    const forms = (data.forms || []).slice(0, 8);
    const holder = $("suggest");
    holder.innerHTML = "";
    forms.forEach((f) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = f.name;
      b.addEventListener("click", () => ask(`${f.name} — how do I apply, step by step?`));
      holder.appendChild(b);
    });
    const select = $("app-form-select");
    select.innerHTML = `<option value="">${esc(t("track.custom"))}</option>`;
    forms.forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f.id;
      opt.textContent = f.name;
      select.appendChild(opt);
    });
  } catch { /* ignore */ }
}

/* ============================== tracker ============================== */

async function refreshTracker() {
  if (!state.user) return;
  try {
    const data = await api("/api/applications");
    const apps = data.applications || [];
    $("app-list").innerHTML = apps.length
      ? apps.map(appCard).join("")
      : `<p class="muted">${esc(t("track.gate"))}</p>`;
    const alerts = await api("/api/alerts");
    const items = alerts.alerts || [];
    $("alerts-strip").innerHTML = items
      .filter((a) => a.kind === "warning")
      .slice(0, 4)
      .map((a) => `<p class="strip-alert">${esc(clip(a.title, 160))}</p>`)
      .join("");
  } catch { /* ignore */ }
}

function appCard(app) {
  const days = app.days_left;
  let due = "";
  if (days !== null && days !== undefined) {
    due = days < 0 ? `${Math.abs(days)} ${t("days.past")}` : days === 0 ? t("days.today") : `${days} ${t("days.left")}`;
  }
  const statusOptions = Object.entries(I18N.en)
    .filter(([k]) => k.startsWith("status."))
    .map(([k]) => k.slice(7))
    .map((s) => `<option value="${s}" ${s === app.status ? "selected" : ""}>${esc(t("status." + s))}</option>`)
    .join("");
  const events = (app.events || []).map((ev) =>
    `<div class="event-row"><span class="event-dot"></span><span class="event-status">${esc(t("status." + ev.status) || ev.status)}</span>
     <span class="muted small">${esc(fmtDate(ev.at))}${ev.note ? " · " + esc(clip(ev.note, 120)) : ""}</span></div>`).join("");
  return `
    <div class="app-card" data-app="${app.id}">
      <div class="app-head">
        <h3>${esc(clip(app.form_name, 120))}</h3>
        <span class="status-pill ${esc(app.status)}">${esc(t("status." + app.status))}</span>
      </div>
      <div class="app-meta">
        ${app.office ? `<span>${esc(clip(app.office, 100))}</span>` : ""}
        ${app.reference_no ? `<span class="mono">${esc(app.reference_no)}</span>` : ""}
        ${app.target_date ? `<span>${esc(fmtDate(app.target_date))} · ${esc(due)}</span>` : ""}
      </div>
      <div class="app-controls">
        <label class="visually-hidden">Status</label>
        <select data-status-select="${app.id}">${statusOptions}</select>
        <button class="link-btn" type="button" data-app-note="${app.id}">+ note</button>
        ${app.form_id ? `<button class="link-btn" type="button" data-pdf-form="${esc(app.form_id)}">${esc(t("btn.pdf"))}</button>` : ""}
        <button class="link-btn danger" type="button" data-app-del="${app.id}">${esc(t("btn.delete"))}</button>
      </div>
      <details class="app-events"><summary>${(app.events || []).length} events</summary>${events}</details>
    </div>`;
}

$("app-new-btn").addEventListener("click", () => {
  $("app-form").hidden = !$("app-form").hidden;
});
$("app-cancel").addEventListener("click", () => { $("app-form").hidden = true; });

$("app-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/applications", {
      method: "POST",
      body: {
        form_id: $("app-form-select").value,
        form_name: $("app-name").value.trim(),
        office: $("app-office").value.trim(),
        reference_no: $("app-ref").value.trim(),
        target_date: $("app-date").value || null,
        notes: $("app-notes").value.trim(),
        remind_days: Number($("app-remind").value) || 3,
      },
    });
    $("app-form").hidden = true;
    $("app-name").value = "";
    $("app-office").value = "";
    $("app-ref").value = "";
    $("app-date").value = "";
    $("app-notes").value = "";
    toast(t("toast.saved"));
    refreshTracker();
  } catch (err) { toast(err.message); }
});

$("app-list").addEventListener("change", async (e) => {
  const select = e.target.closest("[data-status-select]");
  if (!select) return;
  try {
    await api(`/api/applications/${select.dataset.statusSelect}`, {
      method: "PATCH",
      body: { status: select.value },
    });
    toast(t("toast.saved"));
    refreshTracker();
    refreshAlertsBadge();
  } catch (err) { toast(err.message); }
});

$("app-list").addEventListener("click", async (e) => {
  const noteBtn = e.target.closest("[data-app-note]");
  const delBtn = e.target.closest("[data-app-del]");
  try {
    if (noteBtn) {
      const note = window.prompt("Note:");
      if (!note) return;
      const app = (await api(`/api/applications/${noteBtn.dataset.appNote}`));
      await api(`/api/applications/${noteBtn.dataset.appNote}/events`, {
        method: "POST",
        body: { status: app.status, note },
      });
      refreshTracker();
    } else if (delBtn) {
      await api(`/api/applications/${delBtn.dataset.appDel}`, { method: "DELETE" });
      toast(t("toast.deleted"));
      refreshTracker();
    }
  } catch (err) { toast(err.message); }
});

/* ============================== for you ============================== */

let foryouLoaded = false;

async function refreshForYou() {
  if (!state.user) return;
  try {
    const role = $("role-select").value || state.user.role || "citizen";
    const data = await api(`/api/recommendations?role=${encodeURIComponent(role)}`);
    $("foryou-list").innerHTML = (data.for_you || []).map(schemeCard).join("") ||
      `<p class="muted">${esc(t("err.generic"))}</p>`;
    const also = data.also_useful || [];
    $("foryou-also-title").hidden = !also.length;
    $("foryou-also").innerHTML = also.map(schemeCard).join("");
    foryouLoaded = true;
  } catch { /* ignore */ }
}

$("role-select").addEventListener("change", refreshForYou);

function schemeCard(s) {
  const block = (label, items) => (items && items.length)
    ? `<div class="scheme-block"><p class="section-label">${esc(label)}</p><ul class="plain-list">${items.map((x) => `<li>${esc(clip(x, 300))}</li>`).join("")}</ul></div>`
    : "";
  const where = typeof s.where_to_go === "object" && s.where_to_go ? s.where_to_go : {};
  const whereText = [where.office, where.note].filter(Boolean).join(" — ");
  const speakText = [s.name, s.summary, ...(s.benefits || [])].filter(Boolean).join(". ");
  return `
    <div class="scheme-card">
      <h3>${esc(s.name)}</h3>
      <p class="scheme-summary">${esc(clip(s.summary, 300))}</p>
      ${block(t("foryou.benefits"), s.benefits)}
      ${block(t("foryou.eligibility"), s.eligibility)}
      ${block(t("foryou.documents"), s.documents)}
      ${block(t("foryou.costs"), s.extra_costs)}
      ${whereText ? `<div class="scheme-block"><p class="section-label">${esc(t("foryou.where"))}</p><p>${esc(clip(whereText, 300))}</p></div>` : ""}
      ${block(t("foryou.forms"), s.form_names || [])}
      ${block(t("foryou.steps"), s.steps)}
      ${block(t("foryou.warnings"), s.warnings)}
      <div class="result-tools">
        ${speakButton(t("btn.read"), speakText)}
        <button class="link-btn" type="button" data-pdf-scheme="${esc(s.id)}">PDF</button>
        ${s.official_url ? `<a class="link-btn" href="${esc(s.official_url)}" target="_blank" rel="noopener noreferrer">${esc(t("foryou.official"))}</a>` : ""}
      </div>
    </div>`;
}

document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-pdf-scheme]");
  if (btn) downloadPdf(`/api/pdf/scheme/${encodeURIComponent(btn.dataset.pdfScheme)}?lang=${state.lang}`);
});

/* ============================== centres ============================== */

let centresLoaded = false;

async function loadCentres(force = false) {
  if (centresLoaded && !force) return;
  try {
    const data = await api("/api/centres");
    const select = $("centre-service");
    if (!select.options.length) {
      const any = document.createElement("option");
      any.value = "";
      any.textContent = t("centres.any");
      select.appendChild(any);
      (data.services || []).forEach((s) => {
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = s.name;
        select.appendChild(opt);
      });
    }
    renderCentres(data.centres || []);
    centresLoaded = true;
  } catch { /* ignore */ }
}

$("centres-filters").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const service = $("centre-service").value;
    const area = $("centre-area").value.trim();
    const data = await api(`/api/centres?service=${encodeURIComponent(service)}&area=${encodeURIComponent(area)}`);
    renderCentres(data.centres || []);
  } catch (err) { toast(err.message); }
});

function renderCentres(centres) {
  const holder = $("centre-list");
  if (!centres.length) {
    holder.innerHTML = `<p class="muted">${esc(t("centres.none"))}</p>`;
    return;
  }
  holder.innerHTML = centres.map((c) => {
    const maps = "https://www.google.com/maps/search/?api=1&query=" +
      encodeURIComponent(`${c.name} ${c.address} ${c.district} ${c.state}`);
    const services = (c.services || []).slice(0, 6).join(", ");
    return `
      <div class="centre-card">
        <p class="centre-type">${esc(clip(c.type, 60))}</p>
        <h3>${esc(clip(c.name, 120))}</h3>
        <p class="centre-address">${esc(clip(c.address, 200))}${c.district ? ", " + esc(c.district) : ""}${c.state ? ", " + esc(c.state) : ""}</p>
        ${c.hours ? `<p class="muted small">${esc(c.hours)}</p>` : ""}
        ${c.phone ? `<p class="muted small">${esc(c.phone)}</p>` : ""}
        ${services ? `<p class="muted small">${esc(t("centres.services"))}: ${esc(services)}</p>` : ""}
        <a class="link-btn" href="${esc(maps)}" target="_blank" rel="noopener noreferrer">${esc(t("centres.maps"))}</a>
      </div>`;
  }).join("");
}

/* ============================== boot ============================== */

async function boot() {
  applyI18n();
  applyComfort();
  bindComfort();
  await initLanguages();
  applyI18n();
  await loadMe();
  await loadSuggestions();
  await loadPrivacyNote();
  try {
    const h = await api("/api/health");
    if (h && h.model) $("footer-model").textContent = `Powered by Gemma 4 · ${h.model} via the Gemini API`;
  } catch { /* ignore */ }
  if (state.user) {
    refreshAlertsBadge();
    setInterval(refreshAlertsBadge, 60000);
  }
  if (!ttsSupported()) {
    document.querySelectorAll(".speak-btn").forEach((b) => { b.hidden = true; });
  }
}

boot();
