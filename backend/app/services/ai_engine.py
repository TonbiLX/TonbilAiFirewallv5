# --- Ajan: ANALIST (THE ANALYST) ---
# TonbilAi NLP Motoru: TF-IDF + Fuzzy Matching ile Turkce dogal dil anlama.
# Intent siniflandirma, entity cikarma, coklu komut ayristirma.
# Cihaz alias sistemi, iliski anahtar kelimeleri, yaklasik IP eslestirme.

import re
import os
import json
import math
from collections import Counter
from dataclasses import dataclass, field

# --- Veri Yapilari ---

@dataclass
class Entity:
    """Cikarilan varlik (cihaz, domain, profil, port, vb.)"""
    type: str        # device, domain, profile, port, category, service
    value: str       # Cozumlenmis deger (IP, domain adi, profil adi vb.)
    original: str    # Kullanıcınin yazdigi orijinal metin
    confidence: float = 1.0
    metadata: dict = field(default_factory=dict)

@dataclass
class ParsedCommand:
    """Ayristirilmis tek bir komut."""
    intent: str
    confidence: float
    entities: list[Entity]
    original_text: str

# --- Bilinen Servisler -> Domain Mapping ---
SERVICE_DOMAINS = {
    "facebook": ["facebook.com", "fb.com", "fbcdn.net", "facebook.net"],
    "instagram": ["instagram.com", "cdninstagram.com"],
    "twitter": ["twitter.com", "x.com", "twimg.com"],
    "tiktok": ["tiktok.com", "tiktokcdn.com", "musical.ly"],
    "youtube": ["youtube.com", "youtu.be", "ytimg.com", "googlevideo.com"],
    "netflix": ["netflix.com", "nflxvideo.net", "nflximg.net"],
    "whatsapp": ["whatsapp.com", "whatsapp.net"],
    "telegram": ["telegram.org", "t.me", "telegram.me"],
    "discord": ["discord.com", "discord.gg", "discordapp.com"],
    "twitch": ["twitch.tv", "twitchcdn.net"],
    "reddit": ["reddit.com", "redd.it", "redditstatic.com"],
    "spotify": ["spotify.com", "scdn.co", "spotifycdn.com"],
    "pinterest": ["pinterest.com", "pinimg.com"],
    "snapchat": ["snapchat.com", "snap.com", "sc-cdn.net"],
    "linkedin": ["linkedin.com", "licdn.com"],
    "amazon": ["amazon.com", "amazon.com.tr", "amazonaws.com"],
    "aliexpress": ["aliexpress.com", "alibaba.com"],
    "trendyol": ["trendyol.com"],
    "hepsiburada": ["hepsiburada.com"],
    "steam": ["steampowered.com", "steamcommunity.com", "steamstatic.com"],
    "roblox": ["roblox.com", "rbxcdn.com"],
    "minecraft": ["minecraft.net", "mojang.com"],
    "fortnite": ["epicgames.com", "fortnite.com"],
    "valorant": ["playvalorant.com", "riotgames.com"],
    "lol": ["leagueoflegends.com", "riotgames.com"],
    "pubg": ["pubg.com", "playbattlegrounds.com"],
    "bet365": ["bet365.com"],
    "iddaa": ["iddaa.com", "nesine.com", "misli.com", "bilyoner.com"],
    "bahis": ["bet365.com", "bets10.com", "1xbet.com", "nesine.com", "misli.com"],
    "porn": ["pornhub.com", "xvideos.com", "xhamster.com", "xnxx.com"],
    "gambling": ["bet365.com", "bets10.com", "1xbet.com", "nesine.com"],
    "google": ["google.com", "google.com.tr", "googleapis.com"],
    "gmail": ["gmail.com", "mail.google.com"],
    "zoom": ["zoom.us", "zoom.com"],
    "teams": ["teams.microsoft.com", "microsoft.com"],
}

# Turkce karakter normalizasyon tablosu
TR_CHAR_MAP = str.maketrans(
    "çğıöşüÇĞİÖŞÜâîûÂÎÛ",
    "cgiosuCGIOSUaiuAIU"
)

def normalize_turkish(text: str) -> str:
    """Turkce karakterleri ASCII'ye donustur, kucuk harfe cevir."""
    return text.lower().translate(TR_CHAR_MAP)


# --- Cihaz Alias Sistemi ---

ALIAS_FILE_PATH = os.environ.get("ALIAS_FILE_PATH", "/opt/tonbilaios/backend/data/device_aliases.json")


def load_aliases() -> dict:
    """Alias JSON dosyasindan alias sozlugunu yukle. Dosya yoksa bos dict dondur."""
    try:
        if os.path.exists(ALIAS_FILE_PATH):
            with open(ALIAS_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("aliases", {})
    except (json.JSONDecodeError, OSError, PermissionError):
        pass
    return {}


def save_aliases(aliases: dict) -> None:
    """Alias sozlugunu JSON dosyasina kaydet."""
    data = {"aliases": aliases}
    dir_path = os.path.dirname(ALIAS_FILE_PATH)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    with open(ALIAS_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_alias(alias_name: str, device_id: int, ip: str) -> None:
    """Yeni alias ekle veya mevcut olani güncelle."""
    aliases = load_aliases()
    key = normalize_turkish(alias_name.strip())
    aliases[key] = {"device_id": device_id, "ip": ip}
    save_aliases(aliases)


def remove_alias(alias_name: str) -> bool:
    """Alias sil. Başarılı ise True dondur."""
    aliases = load_aliases()
    key = normalize_turkish(alias_name.strip())
    if key in aliases:
        del aliases[key]
        save_aliases(aliases)
        return True
    return False


def find_device_by_alias(text: str, aliases: dict) -> Entity | None:
    """
    Metin içinde alias eslesmesi ara. Fuzzy match ile en iyi eşleşen alias'i dondur.
    Hem birlestik metin hem de iliski+cihaz_tipi kombinasyonunu dener.
    """
    if not aliases:
        return None

    text_norm = normalize_turkish(text)
    alias_keys = list(aliases.keys())

    # 1. Tam icerme kontrolü (en yuksek öncelik)
    best_match_key = None
    best_match_len = 0
    for akey in alias_keys:
        if akey in text_norm and len(akey) > best_match_len:
            best_match_key = akey
            best_match_len = len(akey)

    if best_match_key:
        info = aliases[best_match_key]
        return Entity(
            type="device",
            value=info.get("ip", ""),
            original=best_match_key,
            confidence=0.95,
            metadata={"device_id": info.get("device_id"), "alias": best_match_key, "source": "alias"},
        )

    # 2. Fuzzy match
    match, score = fuzzy_match_best(text_norm, alias_keys, threshold=0.65)
    if match:
        info = aliases[match]
        return Entity(
            type="device",
            value=info.get("ip", ""),
            original=match,
            confidence=score,
            metadata={"device_id": info.get("device_id"), "alias": match, "source": "alias"},
        )

    # 3. Iliski + cihaz tipi kombinasyonu ile ara
    rel_found = _extract_relationship(text_norm)
    dev_type_found = _extract_device_type(text_norm)
    if rel_found and dev_type_found:
        combo = f"{rel_found} {dev_type_found}"
        combo_norm = normalize_turkish(combo)
        # Combo ile alias anahtarlarini karsilastir
        match, score = fuzzy_match_best(combo_norm, alias_keys, threshold=0.60)
        if match:
            info = aliases[match]
            return Entity(
                type="device",
                value=info.get("ip", ""),
                original=match,
                confidence=score * 0.9,
                metadata={"device_id": info.get("device_id"), "alias": match, "source": "alias_combo"},
            )

    return None


# --- Iliski ve Cihaz Tipi Anahtar Kelimeleri ---

RELATIONSHIP_KEYWORDS = {
    "baba": ["baba", "babam", "babamin", "babamın", "babamin", "babamın"],
    "anne": ["anne", "annem", "annemin", "annemın"],
    "ogul": ["ogul", "oglum", "oglumun", "oğlum", "oglumun", "oğlumun"],
    "kiz": ["kiz", "kizim", "kızım", "kızımın", "kizimin"],
    "kardes": ["kardes", "kardesim", "kardeşim", "kardesimin"],
    "es": ["es", "esim", "eşim", "eşimin", "esimin"],
    "misafir": ["misafir", "konuk"],
}

DEVICE_TYPE_KEYWORDS = {
    "telefon": ["telefon", "telefonu", "telefonunu", "tel", "phone", "mobil", "cep"],
    "tablet": ["tablet", "tableti", "tabletini", "ipad"],
    "bilgisayar": ["bilgisayar", "bilgisayari", "laptop", "pc", "masaustu"],
    "tv": ["tv", "televizyon", "smart tv", "tivi", "televizyonu"],
}


def _extract_relationship(text_norm: str) -> str | None:
    """Metinden iliski anahtar kelimesi cikar. Normalized metin bekler."""
    for rel_key, variants in RELATIONSHIP_KEYWORDS.items():
        for v in variants:
            v_norm = normalize_turkish(v)
            if v_norm in text_norm:
                return rel_key
    return None


def _extract_device_type(text_norm: str) -> str | None:
    """Metinden cihaz tipi anahtar kelimesi cikar. Normalized metin bekler."""
    for dt_key, variants in DEVICE_TYPE_KEYWORDS.items():
        for v in variants:
            v_norm = normalize_turkish(v)
            if v_norm in text_norm:
                return dt_key
    return None


def extract_relationship_and_device_type(text: str) -> tuple[str | None, str | None]:
    """Metinden iliski ve cihaz tipi bilgisini cikar. Ham metin alir."""
    text_norm = normalize_turkish(text)
    return _extract_relationship(text_norm), _extract_device_type(text_norm)


# --- Basit TF-IDF Implementasyonu (scikit-learn gerektirmez) ---

class SimpleTfIdf:
    """Hafif TF-IDF: scikit-learn olmadan calisan minimal implementasyon."""

    def __init__(self):
        self.vocab: dict[str, int] = {}
        self.idf: dict[str, float] = {}
        self.doc_vectors: list[dict[str, float]] = []
        self.doc_labels: list[str] = []

    def _tokenize(self, text: str) -> list[str]:
        """Basit tokenizer: kelime ve bi-gram cikar."""
        text = normalize_turkish(text)
        # Noktalama temizle ama apostrofleri koru
        text = re.sub(r"[^\w\s']", " ", text)
        words = text.split()
        tokens = list(words)
        # Bi-gramlar ekle
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i+1]}")
        return tokens

    def fit(self, texts: list[str], labels: list[str]):
        """Egitim: IDF hesapla."""
        n_docs = len(texts)
        doc_freq: Counter = Counter()
        self.doc_vectors = []
        self.doc_labels = labels

        all_token_lists = []
        for text in texts:
            tokens = self._tokenize(text)
            all_token_lists.append(tokens)
            unique_tokens = set(tokens)
            for token in unique_tokens:
                doc_freq[token] += 1

        # IDF hesapla
        for token, df in doc_freq.items():
            self.idf[token] = math.log((n_docs + 1) / (df + 1)) + 1

        # TF-IDF vektorleri oluştur
        for tokens in all_token_lists:
            tf = Counter(tokens)
            vec = {}
            for token, count in tf.items():
                tfidf = (count / len(tokens)) * self.idf.get(token, 1.0)
                vec[token] = tfidf
            self.doc_vectors.append(vec)

    def predict(self, text: str, top_k: int = 3) -> list[tuple[str, float]]:
        """En yakin intent'leri dondur (label, similarity)."""
        tokens = self._tokenize(text)
        tf = Counter(tokens)
        query_vec = {}
        for token, count in tf.items():
            tfidf = (count / len(tokens)) * self.idf.get(token, 1.0)
            query_vec[token] = tfidf

        scores: dict[str, list[float]] = {}
        for i, doc_vec in enumerate(self.doc_vectors):
            sim = self._cosine_sim(query_vec, doc_vec)
            label = self.doc_labels[i]
            if label not in scores:
                scores[label] = []
            scores[label].append(sim)

        # Her intent için en iyi skoru al
        best_scores = []
        for label, sims in scores.items():
            best_scores.append((label, max(sims)))

        best_scores.sort(key=lambda x: x[1], reverse=True)
        return best_scores[:top_k]

    @staticmethod
    def _cosine_sim(a: dict, b: dict) -> float:
        """Iki sparse vektor arasi cosine similarity."""
        common = set(a.keys()) & set(b.keys())
        if not common:
            return 0.0
        dot = sum(a[k] * b[k] for k in common)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# --- Fuzzy String Matching (harici kutuphane gerektirmez) ---

def levenshtein_ratio(s1: str, s2: str) -> float:
    """Levenshtein mesafesi tabanli benzerlik oranı (0-1)."""
    s1 = normalize_turkish(s1)
    s2 = normalize_turkish(s2)
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    # Optimize: eger biri digerinin içinde geciyorsa yuksek skor ver
    if s1 in s2 or s2 in s1:
        return max(len1, len2) / (max(len1, len2) + abs(len1 - len2) + 1)
    # Levenshtein DP
    matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1):
        matrix[i][0] = i
    for j in range(len2 + 1):
        matrix[0][j] = j
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i-1] == s2[j-1] else 1
            matrix[i][j] = min(
                matrix[i-1][j] + 1,
                matrix[i][j-1] + 1,
                matrix[i-1][j-1] + cost,
            )
    distance = matrix[len1][len2]
    max_len = max(len1, len2)
    return 1.0 - (distance / max_len)


def fuzzy_match_best(query: str, candidates: list[str], threshold: float = 0.55) -> tuple[str | None, float]:
    """En iyi eşleşen adayi dondur."""
    query_norm = normalize_turkish(query)
    best_match = None
    best_score = 0.0
    for candidate in candidates:
        cand_norm = normalize_turkish(candidate)
        # Tam icerme bonus
        if query_norm in cand_norm or cand_norm in query_norm:
            score = 0.9
        else:
            score = levenshtein_ratio(query_norm, cand_norm)
        if score > best_score:
            best_score = score
            best_match = candidate
    if best_score >= threshold:
        return best_match, best_score
    return None, 0.0


# --- Intent Tanimlari ve Egitim Verileri ---

INTENT_TRAINING = {
    "block_domain": [
        "facebook engelle",
        "youtube engelle",
        "youtube u engelle",
        "youtube'u kapat",
        "netflix engelle",
        "netflix i engelle",
        "instagram engelle",
        "instagram'a erişimi kapat",
        "tiktok engelle",
        "tiktok'u yasakla",
        "twitter engelle",
        "whatsapp engelle",
        "discord engelle",
        "bu siteyi engelle",
        "sosyal medyayi engelle",
        "oyun sitelerini kapat",
        "bahis sitelerini engelle",
        "kumar sitelerini engelle",
        "yetişkin siteleri engelle",
        "porno siteleri engelle",
        "reklam sitelerini engelle",
        "domain engelle",
        "siteyi blokla",
        "erişimi engelle",
        "siteye girilemesin",
        "bu adrese erişim olmasin",
        "interneti kisitla",
        "erişimi kes",
        "yasakla",
        "bloke et",
        "facebook netflix youtube engelle",
        "su siteleri engelle",
        "çocuklar youtube izlemesin",
        "çocuklar için youtube kapat",
        "cocugum tiktok a girmesin",
        "instagram ve tiktok kapat",
        "instagram ve tiktok engelle",
        "instagram tiktok youtube engelle",
        "facebook ve instagram kapat",
        "youtube ve netflix engelle",
        "sosyal medya uygulamalarini engelle",
        "su uygulamalari engelle",
        "bu sitelere girilemesin",
        "bu servisleri kapat",
        "erişimi engelle sitelerin",
        "youtube.com engelle",
        "facebook.com engelle",
        "example.com engelle",
    ],
    "unblock_domain": [
        "facebook engelini kaldir",
        "youtube u ac",
        "netflix i serbest birak",
        "siteyi ac",
        "domain engelini kaldir",
        "erişime ac",
        "yasagi kaldir",
        "engeli kaldir",
        "serbest birak",
        "izin ver",
        "erişim izni ver",
        "tekrar acilsin",
        "geri ac",
        "youtube engellemeyi kaldir",
        "youtube engelini ac",
        "youtube engeli kaldir",
        "youtube.com engelini kaldir",
        "instagram engeli kapat",
        "tiktok engeli kaldir",
        "facebook serbest birak",
        "twitter engelini ac",
    ],
    "block_device_domain": [
        "babamin telefonunda youtube engelle",
        "cocugun tabletinde tiktok kapat",
        "misafir cihazinda instagram engelle",
        "bu cihazda facebook engelle",
        "telefonda su siteyi engelle",
        "tablette youtube yasakla",
        "cihazda domain engelle",
        "cihazda siteyi kapat",
        "babamin telefonunda instagram ve tiktok engelle",
        "cocugun tabletinde netflix kapat",
        "su cihazda su siteyi engelle",
        "cihaz için site engelle",
        "cihaz için domain engelle",
        "babamin telefonunda porno siteleri engelle",
        "cocugun tabletinde oyun siteleri kapat",
        "192.168.1.10 için youtube engelle",
        "192.168.1.40 da facebook engelle",
        "192.168.1.10 cihazinda facebook engelle",
        "192.168.1.15 için instagram kapat",
        "192.168.1.10 için tiktok engelle",
        "192.168.1.10 cihazinda netflix engelle",
        "192.168.1.40 için youtube kapat",
        "su ip için youtube engelle",
        "su ip adresinde facebook kapat",
    ],
    "unblock_device_domain": [
        "babamin telefonunda youtube engelini kaldir",
        "cocugun tabletinde tiktok acilsin",
        "cihazda facebook engelini kaldir",
        "telefonda su sitenin engelini ac",
        "tablette youtube serbest birak",
        "cihazda domain izin ver",
        "cihaz için site engeli kaldir",
        "babamin telefonunda instagram serbest birak",
        "cocugun tabletinde netflix ac",
        "su cihazda su sitenin engeli kaldirilsin",
        "cihazda engeli kaldir sitenin",
        "telefonda erişim izni ver",
        "192.168.1.10 için youtube engelini kaldir",
        "192.168.1.40 da facebook engeli kaldir",
        "192.168.1.10 cihazinda youtube ac",
        "192.168.1.15 için instagram engeli kaldir",
        "192.168.1.10 için tiktok serbest birak",
        "192.168.1.10 cihazinda netflix engelini kaldir",
        "192.168.1.40 için youtube engellemeyi kaldir",
        "su ip için youtube engeli kaldir",
        "su ip adresinde facebook engelini ac",
        "192.168.1.10 youtube engeli kaldir",
    ],
    "block_device": [
        "cihazi engelle",
        "cihazin internetini kes",
        "interneti kapat",
        "erişimini engelle",
        "cihazi blokla",
        "telefonu engelle",
        "bilgisayari engelle",
        "tableti engelle",
        "internetten kes",
        "agdan cikar",
        "bağlantısini kes",
        "bu cihaz internete giremesin",
        "erişimi durdur",
        "babamin telefonunu engelle",
        "cocugun tabletini kapat",
        "misafir cihazini engelle",
        "çocuklarin interneti kapatilsin",
        "çocuklarin erişimi kesilsin",
        "çocuklarin interneti kesilsin",
        "internet erişimini kapat",
        "bu cihazin interneti kesilsin",
        "internetini kes",
    ],
    "unblock_device": [
        "cihazin engelini kaldir",
        "interneti geri ac",
        "erişimini ac",
        "cihazi serbest birak",
        "engeli kaldir",
        "tekrar baglat",
        "internete erissin",
        "bağlantısini ac",
        "agdan engeli kaldir",
    ],
    "assign_profile": [
        "profil ata",
        "profil ayarla",
        "profilini değiştir",
        "çocuk profili ata",
        "yetişkin profili yap",
        "misafir profili ata",
        "cihazin profilini değiştir",
        "su cihaza çocuk profili ata",
        "babamin telefonuna yetişkin profili ata",
        "tablet için çocuk profili ayarla",
        "profil olarak ayarla",
        "profilini çocuk yap",
    ],
    "list_devices": [
        "cihazlari listele",
        "cihazlari goster",
        "bagli cihazlar",
        "agdaki cihazlar",
        "online cihazlar",
        "çevrimiçi cihazlar",
        "kimler bagli",
        "agda ne var",
        "agda kimler var",
        "hangi cihazlar bagli",
        "cihaz listesi",
        "tum cihazlar",
        "kac cihaz var",
    ],
    "list_profiles": [
        "profilleri listele",
        "profilleri goster",
        "mevcut profiller",
        "profil listesi",
        "hangi profiller var",
        "profiller neler",
    ],
    "system_status": [
        "sistem durumu",
        "ag durumu",
        "nasil gidiyor",
        "özet goster",
        "genel durum",
        "istatistikler",
        "dashboard özeti",
        "sistem nasil",
        "router durumu",
        "durum raporu",
        "ag özeti",
        "ne durumda",
    ],
    "dns_stats": [
        "dns istatistikleri",
        "dns durumu",
        "engelleme istatistikleri",
        "kac domain engelli",
        "dns sorgu sayısı",
        "engellenen siteler",
        "blocklist durumu",
    ],
    "open_port": [
        "port ac",
        "portu ac",
        "port acilsin",
        "firewall port ac",
        "su portu ac",
        "erişime ac portu",
        "port izin ver",
        "port 443 tcp ac",
        "udp port ac",
        "ssh portunu ac",
        "http portunu ac",
    ],
    "close_port": [
        "port kapat",
        "portu kapat",
        "portu engelle",
        "port kapatilsin",
        "firewall port kapat",
        "su portu engelle",
        "port 22 tcp kapat",
        "udp portu engelle",
    ],
    "block_category": [
        "kategori engelle",
        "kumar kategorisini engelle",
        "yetişkin içerik engelle",
        "sosyal medya kategorisi kapat",
        "oyun kategorisini engelle",
        "reklam kategorisini engelle",
        "streaming engelle",
        "içerik filtresi etkinlestir",
    ],
    "unblock_category": [
        "kategori engelini kaldir",
        "kumar kategorisini ac",
        "sosyal medya kategorisini serbest birak",
        "kategori iznini ver",
        "içerik filtresini kapat",
    ],
    "vpn_status": [
        "vpn durumu",
        "vpn nasil",
        "vpn bagli mi",
        "vpn aktif mi",
        "dis vpn durumu",
        "vpn bilgileri",
    ],
    "vpn_connect": [
        "vpn baglan",
        "vpn ac",
        "vpn etkinlestir",
        "vpn basla",
        "turkiye vpn baglan",
        "almanya vpn ac",
        "amerika vpn",
        "dis vpn aktif et",
    ],
    "vpn_disconnect": [
        "vpn kapat",
        "vpn kes",
        "vpn durdur",
        "vpn devre disi birak",
        "vpn bağlantısini kes",
    ],
    "bandwidth_limit": [
        "bant genisligi sinirla",
        "hiz sinirla",
        "indirme hizi sinirla",
        "internet hizini kisitla",
        "mbps sinir koy",
        "hiz limiti ayarla",
    ],
    "dhcp_info": [
        "dhcp durumu",
        "ip adresleri",
        "dhcp kiralama",
        "ip dagitimi",
        "dhcp bilgileri",
        "hangi ip kimde",
    ],
    "firewall_info": [
        "firewall durumu",
        "güvenlik duvarı",
        "firewall bilgileri",
        "güvenlik duvarı durumu",
    ],
    "list_rules": [
        "firewall kurallarini goster",
        "kurallari listele",
        "aktif kurallar neler",
        "tum kurallari goster",
        "firewall kurallari neler",
        "hangi kurallar var",
        "kural listesi",
        "inbound kurallari goster",
        "outbound kurallari listele",
        "firewall kurallari",
        "aktif kurallar",
    ],
    "add_rule": [
        "firewall kuralı ekle",
        "yeni kural ekle",
        "kural oluştur",
        "port kuralı ekle",
        "accept kuralı ekle",
        "drop kuralı ekle",
        "kural tanimla",
    ],
    "delete_rule": [
        "kural sil",
        "firewall kuralı sil",
        "kuralı kaldir",
        "su kuralı sil",
        "kural kaldir",
        "kuralı cikar",
        "kuralı kaldir",
    ],
    "toggle_rule": [
        "kuralı kapat",
        "kuralı ac",
        "kuralı devre disi birak",
        "kuralı etkinlestir",
        "kuralı aktif yap",
        "kuralı pasif yap",
        "kuralı devreye al",
    ],
    "help": [
        "yardim",
        "help",
        "ne yapabilirsin",
        "neler yapabilirsin",
        "komutlar",
        "yeteneklerin",
        "nasil kullanilir",
        "ornek komutlar",
        "bana yardim et",
    ],
    "greeting": [
        "merhaba",
        "selam",
        "hey",
        "nasilsin",
        "iyi gunler",
        "iyi aksamlar",
        "hosgeldin",
    ],
    "threat_status": [
        "tehdit durumu",
        "tehdit istatistikleri",
        "güvenlik durumu",
        "saldırı durumu",
        "engellenen IP'ler",
        "engelli IP listesi",
        "tehditler",
        "saldırılar",
        "dns tehdit",
        "dis saldırı",
        "flood durumu",
        "tehdit analizi",
        "güvenlik raporu",
        "kac IP engellendi",
        "şüpheli sorgular",
    ],
    "block_ip": [
        "IP engelle",
        "IP adresini engelle",
        "bu IP yi engelle",
        "su IP engelle",
        "IP blokla",
        "IP yasakla",
        "IP adresini kapat",
        "IP erişimini engelle",
        "su adresi engelle",
    ],
    "unblock_ip": [
        "IP engelini kaldir",
        "IP engeli kaldir",
        "IP serbest birak",
        "IP adresini ac",
        "IP yasagini kaldir",
        "IP blokunu kaldir",
        "su IP nin engelini kaldir",
    ],
    "rename_device": [
        "cihaza isim ver",
        "cihazin adini değiştir",
        "bu cihazin adi ... olsun",
        "cihazi yeniden adlandir",
        "hostname değiştir",
        "takma ad ver",
        "lakap ver",
        "bu babamin telefonu",
        "bu oglumun tableti",
        "bu salon tv",
        "su cihaz babamin",
        "buna babamin telefonu de",
        "adini değiştir",
        "alias ver",
        "alias ekle",
        "isim ata",
        "cihaz ismi değiştir",
        "buna isim ver",
        "su cihaza isim ver",
    ],
    "find_device": [
        "babamin telefonu hangisi",
        "oglumun tableti nerede",
        "bu cihaz kimin",
        "su IP kimin",
        "192.168 ile baslayan cihaz",
        "cihazi bul",
        "hangi cihaz bu",
        "kim bu",
        "cihaz ara",
        "cihaz bul",
        "bu cihaz ne",
        "su IP hangi cihaz",
        "annemin telefonu hangisi",
        "esimin tableti nerede",
        "kardesimin bilgisayari hangisi",
    ],
    "pin_ip": [
        "IP sabitle",
        "IP sabitlenmesi",
        "statik IP ata",
        "statik kiralama oluştur",
        "IP adresini sabitle",
        "bu IP yi sabitle",
        "su cihazin IP sini sabitle",
        "mevcut IP sabitle",
        "IP kiralamasini sabitle",
        "bu cihaza sabit IP ver",
        "sabit IP ata",
        "IP rezervasyonu yap",
        "DHCP rezervasyonu",
        "MAC IP eslestir",
        "MAC adresine IP ata",
        "kiralama ekle",
        "kiralama oluştur",
        "statik lease ekle",
        "lease ekle",
        "lease oluştur",
        "cihazin IP sini kaydet",
        "bu IP yi bu cihaza ata",
        "IP ataması yap",
        "babamin telefonunun IP sini sabitle",
        "su cihazin IP si hep ayni kalsin",
        "IP degismesin",
        "sabit adres ver",
    ],
    "query_logs": [
        "loglar",
        "loglari goster",
        "log kayitlari",
        "dns loglari",
        "sorgu loglari",
        "engellenen sorgular",
        "engellenen talepler",
        "engellenmis talepler",
        "engellenmis sorgular",
        "bloke edilen sorgular",
        "engellenen domainler ne",
        "kritik sorgular",
        "kritik talepler",
        "şüpheli sorgular",
        "son sorgular",
        "son dns sorgulari",
        "bugunun loglari",
        "dunun loglari",
        "dunku loglar",
        "2 gun onceki loglar",
        "gecen haftaki loglar",
        "son 1 saatin loglari",
        "bilgisayarimin loglari",
        "bilgisayarimin gönderdiği engellenmis talepler",
        "bilgisayarimin engellenen sorgulari",
        "babamin telefonunun loglari",
        "su cihazin loglari",
        "hangi siteler engellendi",
        "hangi domainler engellendi",
        "engelleme loglari",
        "sorgu gecmisi",
        "dns gecmisi",
        "log analizi",
        "log özeti",
        "log istatistikleri",
        "su IP nin loglari",
        "192.168.1.8 loglari",
        "facebook engellendi mi",
        "youtube sorgusu var mi",
        "kritik sorgu talebi var mi",
        "son engellenen neler",
        "neler engellendi",
        "en cok engellenen domainler",
        "en cok sorgulanan domainler",
        "cihazin sorgu gecmisi",
        "dns sorgu kayitlari",
    ],
}


# --- Zaman Ifadesi Cikarma ---

def extract_time_reference(text: str) -> dict | None:
    """
    Turkce metinden zaman referansi cikar.
    Dondurur: {"days_ago": int} veya {"hours_ago": int} veya None
    """
    text_norm = normalize_turkish(text)

    # "X gun once" / "X gun onceki"
    m = re.search(r"(\d+)\s*gun\s*once", text_norm)
    if m:
        return {"days_ago": int(m.group(1))}

    # "X saat once"
    m = re.search(r"(\d+)\s*saat\s*once", text_norm)
    if m:
        return {"hours_ago": int(m.group(1))}

    # "son X saat"
    m = re.search(r"son\s+(\d+)\s*saat", text_norm)
    if m:
        return {"hours_ago": int(m.group(1))}

    # "son X gun"
    m = re.search(r"son\s+(\d+)\s*gun", text_norm)
    if m:
        return {"days_ago": int(m.group(1))}

    # "son X dakika"
    m = re.search(r"son\s+(\d+)\s*dakika", text_norm)
    if m:
        return {"minutes_ago": int(m.group(1))}

    # "gecen hafta" / "gecen haftaki"
    if "gecen hafta" in text_norm or "onceki hafta" in text_norm:
        return {"days_ago": 7}

    # "bu hafta"
    if "bu hafta" in text_norm:
        return {"days_ago": 7}

    # "dun" / "dunku"
    if "dun" in text_norm or "dunku" in text_norm or "onceki gun" in text_norm:
        return {"days_ago": 1}

    # "bugun" / "bugunun"
    if "bugun" in text_norm:
        return {"days_ago": 0}

    # "su an" / "simdi"
    if "su an" in text_norm or "simdi" in text_norm:
        return {"hours_ago": 1}

    return None


class NLPEngine:
    """TonbilAi NLP Motoru: Intent siniflandirma + Entity cikarma."""

    def __init__(self):
        self.tfidf = SimpleTfIdf()
        self._train()

    def _train(self):
        """TF-IDF modelini egit."""
        texts = []
        labels = []
        for intent, examples in INTENT_TRAINING.items():
            for example in examples:
                texts.append(example)
                labels.append(intent)
        self.tfidf.fit(texts, labels)

    def classify_intent(self, text: str) -> list[tuple[str, float]]:
        """Metin için en olasi intent'leri dondur."""
        return self.tfidf.predict(text, top_k=3)

    def extract_entities(self, text: str, db_context: dict | None = None) -> list[Entity]:
        """Metinden varliklari cikar: cihaz, domain, port, profil, servis."""
        entities = []
        text_norm = normalize_turkish(text)
        db_context = db_context or {}

        # 1. IP adresi cikar (tam IP)
        ip_matches = re.findall(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', text)
        for ip in ip_matches:
            entities.append(Entity(type="ip", value=ip, original=ip))

        # 1b. Yaklasik IP eslestirme (eger tam IP bulunamadıysa)
        if not ip_matches:
            devices = db_context.get("devices", [])
            approx_ip_ent = self._match_approximate_ip(text_norm, text, devices)
            if approx_ip_ent:
                entities.append(approx_ip_ent)

        # 2. Port numarasi cikar
        port_patterns = [
            r'port\s*(\d+)',
            r'(\d+)\s*(?:nolu|numarali)\s*port',
            r'(\d+)\s*/\s*(?:tcp|udp)',
        ]
        for pattern in port_patterns:
            for m in re.finditer(pattern, text_norm):
                port_val = m.group(1)
                if 1 <= int(port_val) <= 65535:
                    entities.append(Entity(type="port", value=port_val, original=m.group(0)))

        # 3. Bilinen servis adlari cikar (facebook, youtube, netflix vb.)
        for service_name, domains in SERVICE_DOMAINS.items():
            sn = normalize_turkish(service_name)
            if sn in text_norm:
                entities.append(Entity(
                    type="service",
                    value=service_name,
                    original=service_name,
                    metadata={"domains": domains},
                ))

        # 4. Açık domain adresi cikar (xxx.com, xxx.com.tr vb.)
        domain_matches = re.findall(
            r'\b([a-zA-Z0-9][\w\-]*\.(?:com|net|org|edu|gov|io|tv|me|tr|com\.tr|edu\.tr|org\.tr|gov\.tr))\b',
            text,
            re.IGNORECASE,
        )
        already_found_domains = set()
        for ent in entities:
            if ent.type == "service":
                already_found_domains.update(ent.metadata.get("domains", []))
        for domain in domain_matches:
            if domain.lower() not in already_found_domains:
                entities.append(Entity(type="domain", value=domain.lower(), original=domain))

        # 5. Alias ile cihaz eslestirme (DB fuzzy match'ten ONCE)
        aliases = load_aliases()
        alias_match = find_device_by_alias(text, aliases)
        if alias_match:
            entities.append(alias_match)

        # 6. Cihaz adi esle (DB'den gelen cihaz listesine karsi fuzzy match)
        # Alias ile zaten bulunduysa atla
        devices = db_context.get("devices", [])
        if devices and not alias_match:
            entities.extend(self._match_devices(text_norm, devices))

        # 7. Profil adi esle
        profiles = db_context.get("profiles", [])
        if profiles:
            entities.extend(self._match_profiles(text_norm, profiles))

        # 8. Kategori adi esle
        categories = db_context.get("categories", [])
        if categories:
            entities.extend(self._match_categories(text_norm, categories))

        # 9. Ülke adi (VPN için)
        country_map = {
            "turkiye": "TR", "turkey": "TR", "tr": "TR",
            "almanya": "DE", "germany": "DE", "de": "DE",
            "amerika": "US", "abd": "US", "usa": "US", "us": "US",
            "ingiltere": "GB", "uk": "GB", "gb": "GB",
            "hollanda": "NL", "nl": "NL", "netherlands": "NL",
            "japonya": "JP", "japan": "JP", "jp": "JP",
            "fransa": "FR", "france": "FR", "fr": "FR",
        }
        for name, code in country_map.items():
            if name in text_norm:
                entities.append(Entity(type="country", value=code, original=name))
                break

        # 10. Iliski ve cihaz tipi bilgisi (metadata olarak)
        rel = _extract_relationship(text_norm)
        dev_type = _extract_device_type(text_norm)
        if rel:
            entities.append(Entity(
                type="relationship",
                value=rel,
                original=rel,
                metadata={"device_type": dev_type},
            ))

        return entities

    def _match_approximate_ip(self, text_norm: str, text_raw: str, devices: list[dict]) -> Entity | None:
        """
        Yaklasik IP eslestirme:
        - "8 li IP" veya "8'li IP" -> sonu .8 olan cihaz
        - "sonu 8 olan" -> sonu .8 olan cihaz
        - "1.40 IP" veya "1.40" -> 192.168.1.40
        - Kismi IP: ".8" veya "1.8" -> sonu .8 veya .1.8 olan cihaz
        """
        if not devices:
            return None

        device_ips = [d.get("ip_address", "") for d in devices if d.get("ip_address")]

        # Pattern 1: "X li IP" veya "X'li IP" (orn: "8 li IP", "8'li IP")
        m = re.search(r"(\d{1,3})\s*['\u2018\u2019]?\s*l[iı]\s*ip", text_norm)
        if m:
            suffix = "." + m.group(1)
            for dev in devices:
                ip = dev.get("ip_address", "")
                if ip.endswith(suffix):
                    return Entity(
                        type="ip", value=ip, original=m.group(0),
                        confidence=0.85,
                        metadata={"device_id": dev.get("id"), "approx_match": True},
                    )

        # Pattern 2: "sonu X olan" (orn: "sonu 8 olan")
        m = re.search(r"sonu\s+(\d{1,3})\s+olan", text_norm)
        if m:
            suffix = "." + m.group(1)
            for dev in devices:
                ip = dev.get("ip_address", "")
                if ip.endswith(suffix):
                    return Entity(
                        type="ip", value=ip, original=m.group(0),
                        confidence=0.85,
                        metadata={"device_id": dev.get("id"), "approx_match": True},
                    )

        # Pattern 3: Kismi IP "X.Y" formatinda (orn: "1.40", "1.8")
        # IP icermeyen metinde kismi IP ara
        m = re.search(r'\b(\d{1,3})\.(\d{1,3})\b', text_raw)
        if m:
            partial = m.group(0)
            # Tam IP degilse (4 oktet degil)
            if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', partial):
                suffix = "." + partial
                for dev in devices:
                    ip = dev.get("ip_address", "")
                    if ip.endswith(suffix):
                        return Entity(
                            type="ip", value=ip, original=partial,
                            confidence=0.80,
                            metadata={"device_id": dev.get("id"), "approx_match": True},
                        )

        return None

    def _match_devices(self, text_norm: str, devices: list[dict]) -> list[Entity]:
        """Cihaz isimlerini fuzzy eslestir. Iliski anahtar kelimeleri ile zenginlestirilmis."""
        found = []
        candidates = {}
        # hostname ve tanim alanlarindan aday oluştur
        for dev in devices:
            hostname = dev.get("hostname", "")
            if hostname:
                candidates[normalize_turkish(hostname)] = dev
            # "baba telefon", "anne tablet" gibi parcali eslesme
            parts = normalize_turkish(hostname).replace("-", " ").replace("_", " ").split()
            for part in parts:
                if len(part) > 2:
                    candidates[part] = dev

        # Metindeki kelimeleri kontrol et
        words = text_norm.split()
        for i, word in enumerate(words):
            if len(word) < 3:
                continue
            # Iki kelimelik bilesik kontrol ("babamin telefonu" -> "baba telefon")
            bigram = f"{words[i-1]} {word}" if i > 0 else ""

            for cand_name, dev in candidates.items():
                # Dogrudan icerme
                if cand_name in text_norm:
                    found.append(Entity(
                        type="device",
                        value=dev.get("ip_address", ""),
                        original=dev.get("hostname", cand_name),
                        confidence=0.9,
                        metadata={"device_id": dev.get("id"), "hostname": dev.get("hostname")},
                    ))
                    return found  # Ilk bulunan yeterli

                # Fuzzy match
                score = levenshtein_ratio(word, cand_name)
                if score > 0.65:
                    found.append(Entity(
                        type="device",
                        value=dev.get("ip_address", ""),
                        original=dev.get("hostname", cand_name),
                        confidence=score,
                        metadata={"device_id": dev.get("id"), "hostname": dev.get("hostname")},
                    ))
                    return found
        return found

    def _match_profiles(self, text_norm: str, profiles: list[dict]) -> list[Entity]:
        """Profil isimlerini fuzzy eslestir."""
        found = []
        profile_keywords = {
            "çocuk": ["çocuk", "child", "kids", "çocuklar"],
            "yetişkin": ["yetişkin", "adult", "buyuk", "ebeveyn"],
            "misafir": ["misafir", "guest", "konuk"],
        }
        for prof in profiles:
            pname = normalize_turkish(prof.get("name", ""))
            ptype = normalize_turkish(prof.get("profile_type", ""))

            # Dogrudan isim eslesme
            if pname in text_norm:
                found.append(Entity(
                    type="profile",
                    value=str(prof.get("id", "")),
                    original=prof.get("name", ""),
                    confidence=0.95,
                    metadata={"profile_name": prof.get("name")},
                ))
                return found

            # Tip bazli anahtar kelime eslesme
            for keyword_group, keywords in profile_keywords.items():
                if keyword_group in ptype or keyword_group in pname:
                    for kw in keywords:
                        if kw in text_norm:
                            found.append(Entity(
                                type="profile",
                                value=str(prof.get("id", "")),
                                original=prof.get("name", ""),
                                confidence=0.85,
                                metadata={"profile_name": prof.get("name")},
                            ))
                            return found
        return found

    def _match_categories(self, text_norm: str, categories: list[dict]) -> list[Entity]:
        """İçerik kategorisi eslestir."""
        found = []
        category_keywords = {
            "gambling": ["kumar", "bahis", "iddaa", "casino"],
            "adult": ["yetişkin", "porno", "adult", "18+", "cinsel"],
            "malicious": ["zararli", "malware", "virus", "phishing"],
            "social_media": ["sosyal medya", "sosyal", "social"],
            "streaming": ["streaming", "video", "dizi", "film"],
            "gaming": ["oyun", "game", "gaming"],
            "ads": ["reklam", "ad", "advertising"],
        }
        for cat in categories:
            cat_key = cat.get("key", "")
            cat_name = normalize_turkish(cat.get("name", ""))

            if cat_name in text_norm:
                found.append(Entity(
                    type="category",
                    value=cat_key,
                    original=cat.get("name", ""),
                    metadata={"category_id": cat.get("id")},
                ))
                continue

            keywords = category_keywords.get(cat_key, [])
            for kw in keywords:
                if kw in text_norm:
                    found.append(Entity(
                        type="category",
                        value=cat_key,
                        original=cat.get("name", ""),
                        metadata={"category_id": cat.get("id")},
                    ))
                    break
        return found

    def parse(self, text: str, db_context: dict | None = None) -> list[ParsedCommand]:
        """
        Tam komut ayristirma: intent siniflandirma + entity cikarma.
        Coklu komutlari da ayristirir (facebook, netflix ve youtube engelle).
        """
        text_clean = text.strip()
        if not text_clean:
            return []

        # Intent siniflandir
        intent_scores = self.classify_intent(text_clean)
        if not intent_scores:
            return [ParsedCommand(intent="unknown", confidence=0.0, entities=[], original_text=text_clean)]

        top_intent, top_score = intent_scores[0]

        # Entity cikar
        entities = self.extract_entities(text_clean, db_context)

        # Coklu servis/domain kontrolü: "facebook, netflix ve youtube engelle"
        services = [e for e in entities if e.type == "service"]
        domains = [e for e in entities if e.type == "domain"]
        other_entities = [e for e in entities if e.type not in ("service", "domain")]

        # Eger birden fazla servis/domain varsa ve intent tekli aksiyon ise -> coklu komut
        multi_targets = services + domains
        if len(multi_targets) > 1 and top_intent in ("block_domain", "unblock_domain"):
            commands = []
            for target in multi_targets:
                cmd = ParsedCommand(
                    intent=top_intent,
                    confidence=top_score,
                    entities=[target] + other_entities,
                    original_text=text_clean,
                )
                commands.append(cmd)
            return commands

        # Tek komut
        return [ParsedCommand(
            intent=top_intent,
            confidence=top_score,
            entities=entities,
            original_text=text_clean,
        )]


# Singleton motor instance
_engine: NLPEngine | None = None

def get_engine() -> NLPEngine:
    """Singleton NLP motoru dondur."""
    global _engine
    if _engine is None:
        _engine = NLPEngine()
    return _engine
