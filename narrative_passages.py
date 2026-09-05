"""
narrative_passages.py

A catalog of well-known multi-verse narrative passages ("Bible stories")
used by narrative_tracker.py. This is the missing piece that makes story-
tracking possible: single-verse semantic search (vector_search.py) can
only match a sentence that closely resembles ONE verse's wording. A
preacher narrating the Prodigal Son in their own words for two minutes
never produces that resemblance — what identifies the story is the whole
passage's content, not any single verse.

Each entry is a passage SUMMARY (a few sentences describing the story's
overall content/arc) used to build one embedding per passage. That
summary embedding is what gets matched against the preacher's rolling
narration window — not the raw verse text.

This list is intentionally a starting set of the most commonly preached
narratives. It's designed to be extended: add a new dict entry per
passage and rebuild the passage index (cheap — a few dozen entries vs
31,000 verses).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NarrativePassage:
    id: str                  # stable key, e.g. "prodigal_son"
    book: str
    book_number: int
    start_chapter: int
    start_verse: int
    end_chapter: int
    end_verse: int
    summary: str              # used to build the passage-level embedding
    title: str                 # human-readable name for UI display


NARRATIVE_PASSAGES: list[NarrativePassage] = [
    NarrativePassage(
        id="psalm_23", book="Psalms", book_number=190,
        start_chapter=23, start_verse=1, end_chapter=23, end_verse=6,
        title="The Shepherd's Psalm",
        summary=(
            "The Lord is my shepherd, I lack nothing. He makes me lie down "
            "in green pastures, he leads me beside quiet waters, he refreshes "
            "my soul. He guides me along the right paths for his name's sake. "
            "Even though I walk through the darkest valley, I will fear no evil, "
            "for you are with me; your rod and your staff, they comfort me. "
            "You prepare a table before me in the presence of my enemies. "
            "You anoint my head with oil; my cup overflows. Surely your goodness "
            "and love will follow me all the days of my life, and I will dwell "
            "in the house of the Lord forever."
        ),
    ),
    NarrativePassage(
        id="prodigal_son", book="Luke", book_number=420,
        start_chapter=15, start_verse=11, end_chapter=15, end_verse=32,
        title="The Prodigal Son",
        summary=(
            "A father has two sons. The younger son asks for his inheritance "
            "early, leaves home, and squanders it all on wild living in a "
            "distant country. A famine comes and he ends up feeding pigs, "
            "starving and ashamed. He decides to return home and confess he "
            "has sinned, planning to ask only to be a servant. His father "
            "sees him coming from far off, runs to him, embraces him, and "
            "celebrates with a feast, giving him a robe and a ring. The "
            "older brother, who stayed and worked faithfully, becomes "
            "angry and jealous that his wasteful brother is celebrated. "
            "The father explains that everything he has belongs to the "
            "faithful son, but his brother who was lost is now found."
        ),
    ),
    NarrativePassage(
        id="david_goliath", book="1 Samuel", book_number=90,
        start_chapter=17, start_verse=1, end_chapter=17, end_verse=58,
        title="David and Goliath",
        summary=(
            "The Philistine army challenges Israel with their champion "
            "Goliath, a giant warrior in armor who mocks Israel's soldiers "
            "for forty days. David, a young shepherd boy bringing food to "
            "his brothers, hears the taunts and volunteers to fight Goliath "
            "despite everyone's doubts about his age and size. King Saul "
            "offers him armor but David refuses it, choosing instead his "
            "sling and five smooth stones. David tells Goliath he comes in "
            "the name of the Lord. He slings a stone that strikes Goliath's "
            "forehead, killing him, then cuts off his head with his own "
            "sword. The Philistine army flees and Israel pursues them."
        ),
    ),
    NarrativePassage(
        id="good_samaritan", book="Luke", book_number=420,
        start_chapter=10, start_verse=25, end_chapter=10, end_verse=37,
        title="The Good Samaritan",
        summary=(
            "A man asks Jesus what he must do to inherit eternal life and "
            "who his neighbor is. Jesus tells a parable: a man traveling "
            "from Jerusalem to Jericho is robbed, beaten, and left for "
            "dead. A priest and a Levite both pass by on the other side "
            "without helping him. A Samaritan, traditionally an enemy of "
            "the Jews, stops, bandages his wounds with oil and wine, puts "
            "him on his own donkey, takes him to an inn, and pays for his "
            "care. Jesus asks which of the three was a true neighbor, and "
            "tells the listener to go and do likewise."
        ),
    ),
    NarrativePassage(
        id="creation_genesis", book="Genesis", book_number=10,
        start_chapter=1, start_verse=1, end_chapter=2, end_verse=3,
        title="Creation",
        summary=(
            "In the beginning God creates the heavens and the earth, which "
            "is formless and dark. God speaks light into existence on the "
            "first day, separates sky and water on the second, creates "
            "land, seas, and plants on the third, sun moon and stars on "
            "the fourth, sea creatures and birds on the fifth, and land "
            "animals and humanity — made in God's image, male and female "
            "— on the sixth day. God blesses humanity and gives them "
            "dominion over creation. On the seventh day God rests, "
            "blessing and sanctifying it."
        ),
    ),
    NarrativePassage(
        id="noahs_ark", book="Genesis", book_number=10,
        start_chapter=6, start_verse=9, end_chapter=9, end_verse=17,
        title="Noah's Ark and the Flood",
        summary=(
            "Seeing the wickedness of humanity, God decides to flood the "
            "earth but instructs righteous Noah to build a large wooden "
            "ark and bring pairs of every kind of animal aboard along with "
            "his family. Rain falls for forty days and nights, flooding "
            "the whole earth and destroying all other life. The ark comes "
            "to rest on Mount Ararat. Noah sends out a dove which "
            "eventually returns with an olive branch, signaling dry land. "
            "God sets a rainbow in the sky as a covenant promise never to "
            "flood the whole earth again."
        ),
    ),
    NarrativePassage(
        id="exodus_red_sea", book="Exodus", book_number=20,
        start_chapter=14, start_verse=1, end_chapter=14, end_verse=31,
        title="Crossing the Red Sea",
        summary=(
            "After Pharaoh lets the Israelites leave Egypt, he changes his "
            "mind and pursues them with his army and chariots. The "
            "Israelites are trapped between Pharaoh's forces and the Red "
            "Sea, and they panic and complain to Moses. Moses stretches "
            "out his hand and God parts the sea, creating a dry path with "
            "walls of water on either side. The Israelites cross safely, "
            "but when the Egyptian army follows, the waters return and "
            "drown Pharaoh's entire army. Israel sings a song of victory "
            "and praise to God on the far shore."
        ),
    ),
    NarrativePassage(
        id="daniel_lions_den", book="Daniel", book_number=270,
        start_chapter=6, start_verse=1, end_chapter=6, end_verse=28,
        title="Daniel in the Lions' Den",
        summary=(
            "Daniel, a trusted official under King Darius, continues to "
            "pray to God three times a day despite a new law forbidding "
            "worship of anyone but the king. Jealous officials trap Daniel "
            "and report him, forcing the king — who respects Daniel but is "
            "bound by his own law — to have him thrown into a den of "
            "lions. The king seals the den with a stone and worries all "
            "night. At dawn he rushes to the den and finds Daniel "
            "completely unharmed, because God sent an angel to shut the "
            "lions' mouths. The king has Daniel's accusers thrown into the "
            "den instead and decrees that all should fear Daniel's God."
        ),
    ),
    NarrativePassage(
        id="jesus_birth", book="Luke", book_number=420,
        start_chapter=2, start_verse=1, end_chapter=2, end_verse=20,
        title="The Birth of Jesus",
        summary=(
            "Caesar Augustus orders a census, requiring Joseph and the "
            "pregnant Mary to travel to Bethlehem. Finding no room at the "
            "inn, Mary gives birth to Jesus in a stable and lays him in a "
            "manger. An angel appears to shepherds in the nearby fields, "
            "announcing the birth of a savior, and a heavenly host praises "
            "God. The shepherds hurry to Bethlehem, find the baby exactly "
            "as described, and spread the news, while Mary treasures these "
            "things in her heart."
        ),
    ),
    NarrativePassage(
        id="jesus_resurrection", book="Luke", book_number=420,
        start_chapter=24, start_verse=1, end_chapter=24, end_verse=12,
        title="The Resurrection",
        summary=(
            "Early on the first day of the week, women come to Jesus' tomb "
            "with spices to anoint his body and find the stone rolled away "
            "and the tomb empty. Two angels appear and ask why they are "
            "looking for the living among the dead, reminding them Jesus "
            "said he would rise on the third day. The women run and tell "
            "the disciples, who at first don't believe them, but Peter "
            "runs to the tomb himself and finds it just as the women said, "
            "leaving amazed."
        ),
    ),
    NarrativePassage(
        id="feeding_5000", book="John", book_number=430,
        start_chapter=6, start_verse=1, end_chapter=6, end_verse=14,
        title="Feeding the Five Thousand",
        summary=(
            "A large crowd follows Jesus, and he tests his disciples by "
            "asking how they will feed everyone. A boy offers five barley "
            "loaves and two small fish, which seems impossibly little for "
            "the crowd. Jesus has everyone sit down, gives thanks, and "
            "distributes the food, which miraculously multiplies until "
            "everyone is fed with plenty left over — twelve baskets of "
            "leftover pieces are gathered. The crowd recognizes this as a "
            "sign and wants to make Jesus king by force."
        ),
    ),
    NarrativePassage(
        id="woman_issue_of_blood", book="Matthew", book_number=400,
        start_chapter=9, start_verse=20, end_chapter=9, end_verse=22,
        title="The Woman with the Issue of Blood",
        summary=(
            "A woman who has suffered from bleeding for twelve years and "
            "spent everything on doctors without being healed pushes through "
            "a crowd surrounding Jesus. She believes that if she can only "
            "touch the hem of his garment or the border of his clothes she "
            "will be made whole. She reaches out, touches his garment, and "
            "is immediately healed. Jesus turns, perceives that power has "
            "gone out from him, and tells her that her faith has made her "
            "whole. The same account appears in Mark where she says if she "
            "may touch but his clothes she shall be whole."
        ),
    ),
    NarrativePassage(
        id="man_born_blind", book="John", book_number=430,
        start_chapter=9, start_verse=1, end_chapter=9, end_verse=41,
        title="Healing the Man Born Blind",
        summary=(
            "Jesus sees a man blind from birth and his disciples ask whether "
            "the man or his parents sinned. Jesus says neither — this happened "
            "so God's works might be revealed. He spits on the ground, makes "
            "clay with the saliva, and anoints or rubs it on the blind man's "
            "eyes. He tells the man to go wash in the pool of Siloam. The man "
            "goes, washes, and comes back seeing. Neighbors debate whether it is "
            "the same man. Pharisees question him and his parents about how he "
            "was healed on the Sabbath."
        ),
    ),
]

# Fast lookup by id for advancing/anchoring logic
PASSAGE_BY_ID: dict[str, NarrativePassage] = {p.id: p for p in NARRATIVE_PASSAGES}
