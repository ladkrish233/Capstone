"""Roman Hinglish -> Devanagari: a small word table first, ITRANS rules as fallback.

Only Latin-letter words are touched. Devanagari, digits and punctuation pass through.
"""
import re

from indic_transliteration import sanscript

# Common Hinglish words whose spelling does not follow ITRANS rules.
WORDS = {
    "aur": "और", "lekin": "लेकिन", "ki": "कि", "ke": "के", "ka": "का", "kee": "की",
    "ko": "को", "se": "से", "me": "में", "mein": "में", "main": "मैं", "mai": "मैं",
    "hum": "हम", "tum": "तुम", "aap": "आप", "tu": "तू", "yeh": "यह", "ye": "ये",
    "woh": "वह", "wo": "वो", "is": "इस", "us": "उस", "isko": "इसको", "usko": "उसको",
    "hai": "है", "hain": "हैं", "ho": "हो", "tha": "था", "thi": "थी", "the": "थे",
    "hoga": "होगा", "hogi": "होगी", "raha": "रहा", "rahi": "रही", "rahe": "रहे",
    "kya": "क्या", "kyun": "क्यों", "kyon": "क्यों", "kaise": "कैसे", "kaisa": "कैसा",
    "kab": "कब", "kahan": "कहाँ", "kaun": "कौन", "kitna": "कितना", "kitne": "कितने",
    "nahi": "नहीं", "nahin": "नहीं", "na": "ना", "haan": "हाँ", "han": "हाँ",
    "ji": "जी", "acha": "अच्छा", "accha": "अच्छा", "achha": "अच्छा", "theek": "ठीक",
    "thik": "ठीक", "bahut": "बहुत", "bohot": "बहुत", "thoda": "थोड़ा", "zyada": "ज़्यादा",
    "jyada": "ज़्यादा", "abhi": "अभी", "phir": "फिर", "fir": "फिर", "ab": "अब",
    "tab": "तब", "jab": "जब", "yahan": "यहाँ", "wahan": "वहाँ", "idhar": "इधर",
    "udhar": "उधर", "sab": "सब", "kuch": "कुछ", "koi": "कोई", "sirf": "सिर्फ़",
    "bhi": "भी", "toh": "तो", "to": "तो", "hi": "ही", "par": "पर", "pe": "पे",
    "bolo": "बोलो", "bol": "बोल", "boliye": "बोलिए", "batao": "बताओ", "bataiye": "बताइए",
    "suno": "सुनो", "suniye": "सुनिए", "dekho": "देखो", "dekhiye": "देखिए",
    "ruko": "रुको", "rukiye": "रुकिए", "chalo": "चलो", "chaliye": "चलिए",
    "karo": "करो", "kijiye": "कीजिए", "karna": "करना", "kar": "कर", "kiya": "किया",
    "karunga": "करूँगा", "karungi": "करूँगी", "de": "दे", "do": "दो",
    "dena": "देना", "lena": "लेना", "le": "ले", "aaya": "आया", "aayi": "आई",
    "aaye": "आए", "gaya": "गया", "gayi": "गई", "gaye": "गए", "samajh": "समझ",
    "samjha": "समझा", "samjhi": "समझी", "samjhe": "समझे", "pata": "पता",
    "mujhe": "मुझे", "tumhe": "तुम्हें", "aapko": "आपको", "humein": "हमें",
    "mera": "मेरा", "meri": "मेरी", "mere": "मेरे", "tera": "तेरा", "tumhara": "तुम्हारा",
    "aapka": "आपका", "aapki": "आपकी", "apna": "अपना", "apni": "अपनी",
    "ek": "एक", "teen": "तीन", "char": "चार", "paanch": "पाँच",
    "minute": "मिनट", "second": "सेकंड", "ghanta": "घंटा", "din": "दिन", "raat": "रात",
    "kal": "कल", "aaj": "आज", "jaldi": "जल्दी", "dhanyavaad": "धन्यवाद",
    "shukriya": "शुक्रिया", "namaste": "नमस्ते", "dost": "दोस्त", "yaar": "यार",
    "bhai": "भाई", "didi": "दीदी", "paisa": "पैसा", "paise": "पैसे", "kaam": "काम",
    "ghar": "घर", "log": "लोग", "baat": "बात", "sahi": "सही", "galat": "ग़लत",
    "mat": "मत", "chahiye": "चाहिए", "milega": "मिलेगा", "milta": "मिलता",
    "sakta": "सकता", "sakti": "सकती", "sakte": "सकते", "wala": "वाला", "wali": "वाली",
    "liye": "लिए", "saath": "साथ", "baad": "बाद", "pehle": "पहले", "andar": "अंदर",
    "bahar": "बाहर", "sach": "सच", "mushkil": "मुश्किल", "aasan": "आसान",
    "friend": "फ्रेंड", "please": "प्लीज़", "sorry": "सॉरी", "thanks": "थैंक्स",
    "hello": "हैलो", "ok": "ओके", "okay": "ओके", "call": "कॉल", "phone": "फ़ोन",
    "meeting": "मीटिंग", "mumbai": "मुंबई", "delhi": "दिल्ली", "rohan": "रोहन",
    "rehta": "रहता", "rahta": "रहता", "rehti": "रहती", "rahti": "रहती", "rehna": "रहना",
    "jaunga": "जाऊँगा", "jaungi": "जाऊँगी", "angrezi": "अंग्रेज़ी", "karoon": "करूँ", "hoon": "हूँ",
    "naam": "नाम", "message": "मैसेज", "time": "टाइम", "problem": "प्रॉब्लम", "office": "ऑफ़िस",
}

_WORD = re.compile(r"[A-Za-z']+")


def _itrans(word: str) -> str:
    w = word.lower().replace("'", "")
    w = w.replace("chh", "Ch").replace("ch", "c")  # Hinglish ch = च, chh = छ
    w = w.replace("w", "v").replace("z", "j").replace("q", "k").replace("x", "ks")
    w = w.replace("f", "ph")
    w = re.sub(r"(?<=[aeiou])h(?=[b-df-hj-np-tv-z])", "ha", w)  # rehta: schwa on h
    w = re.sub(r"(oon|aun|uun)$", lambda m: m.group(1)[:-1] + "M", w)  # hoon -> hoM
    w = re.sub(r"n(?=[kgcjtdp])|m(?=[pb])", "M", w)  # nasal before consonant
    w = w.replace("ee", "ii").replace("oo", "uu") if len(w) > 2 else w
    if w.endswith("a") and not w.endswith("aa"):
        w += "a"  # final a is long in Hinglish (kya, tha, aaya)
    out = sanscript.transliterate(w, sanscript.ITRANS, sanscript.DEVANAGARI)
    return out.rstrip("्")  # no final virama


def to_devanagari(text: str) -> str:
    def repl(m: re.Match) -> str:
        word = m.group(0)
        return WORDS.get(word.lower()) or _itrans(word)

    return _WORD.sub(repl, text)
