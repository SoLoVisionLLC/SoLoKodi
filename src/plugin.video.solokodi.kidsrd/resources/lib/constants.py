SETUP_ADDON_ID = "plugin.program.solokodi.setup"
HTTP_HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
RD_API_ROOT = "https://api.real-debrid.com/rest/1.0"
RD_TOKEN_URL = "https://api.real-debrid.com/oauth/v2/token"
TMDB_API_ROOT = "https://api.themoviedb.org/3"
TMDB_IMAGE_ROOT = "https://image.tmdb.org/t/p/w500"
YTS_API_ROOTS = (
    "https://yts.mx/api/v2",
    "https://yts.lt/api/v2",
    "https://yts.am/api/v2",
)
YTS_API_ROOT = YTS_API_ROOTS[0]
APIBAY_API_ROOTS = (
    "https://apibay.org/q.php",
)
APIBAY_API_ROOT = APIBAY_API_ROOTS[0]

VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".m4v", ".mov", ".wmv", ".webm")

KIDS_KEYWORDS = (
    "kids",
    "kid ",
    "child",
    "children",
    "family",
    "disney",
    "pixar",
    "dreamworks",
    "nickelodeon",
    "nick jr",
    "cartoon",
    "animation",
    "animated",
    "paw patrol",
    "peppa",
    "bluey",
    "sesame",
    "barney",
    "spongebob",
    "minions",
    "frozen",
    "moana",
    "cocomelon",
    "cbeebies",
    "cbeebie",
    "cbeebies",
    "lego",
    "minecraft",
    "pokemon",
    "thomas",
    "dora",
    "curious george",
    "shrek",
    "toy story",
    "finding nemo",
    "lion king",
    "encanto",
    "trolls",
    "sing ",
    "boss baby",
    "kung fu panda",
    "how to train",
    "madagascar",
    "ice age",
    "rugrats",
    "fairly odd",
    "avatar",
    "ben 10",
    "powerpuff",
    "scooby",
    "flintstones",
    "jetsons",
    "smurfs",
    "care bear",
    "my little pony",
    "transformers",
    "teletubbies",
    "wiggles",
    "dora",
    "clifford",
    "arthur",
    "wild kratts",
    "curious",
    "octonauts",
    "pj masks",
    "gabbys",
    "gabby",
    "miraculous",
    "loud house",
    "gravity falls",
    "phineas",
    "ferb",
    "amphibia",
    "owl house",
    "steven universe",
    "adventure time",
    "regular show",
    "gumball",
)
