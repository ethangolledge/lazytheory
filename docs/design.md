# Front-end design

What the app should look and feel like. Design only: no routes, payloads or implementation.

## Rules that hold everywhere

- **Your input is sacred.** What you play, tap or pick is never changed unless you ask. In
  Rhythm, the spine stays exactly as you played it. Ideas sit beside it or on top of it, and
  never replace it.
- **No snapping unless you ask.** Taps keep their timing. Tidying up to a grid is something you
  choose to do, never a side effect of clearing or tapping.
- **No long lists of buttons.** Show a few strong choices, and let you open more on demand.
- **Everything shown is computed.** Nothing is hand-picked to look good. When something is a rule
  of thumb, say so in plain words.
- **Small changes stay small.** Changing one thing never rearranges the rest of the page.
- **Plain language.** "3 against 4", "an 8th early", "one finger moves". Name the theory (tihai,
  polyrhythm, syncopation) but say what it does.

## Look

- Lime on near-black. Hairlines and sharp corners. One bold element per page: the neck, or the
  circle.
- A sans-serif font for everything, and mono only for tab.
- Motion only answers what you do.
- Colours mean roles: the root is lime, chord tones are ink, colour tones are faint.
- Works at phone width with no sideways scrolling.

## Shell

- A sidebar with four sections: Melody, Harmony, Song and Rhythm.
- The key and tuning follow you between sections.
- The URL is the page state, so any view can be shared or bookmarked.

## Melody (was Scales)

- A big title: root and mode ("E Phrygian").
- The notes as chips, labelled by name or by interval (a single toggle for the whole page).
- Pickers for root, mode and tuning:
  - modes are grouped by family, each tagged as sounding major or minor;
  - choosing an instrument offers its tunings by name.
- The neck drawn to scale, high string on top, notes coloured by role.
- A link: "Start a song in E Phrygian".

## Harmony (was Chords)

- The title is the chord symbol, with "Chord iv in E Phrygian" underneath.
- Build it in rows: which degree, what to add (7, 9…), and which bass note.
- Step through the shapes on the neck with ‹ and ›, and show the tab.
- When nothing fits, say why and what to try.

## Song

- **The key at the top.** It can be retuned, and the page says when a tuning changed.
- **Add chords from two sources:** "in the key" (closest to the last chord first) or "any"
  (major and minor on every root). Click one to add it.
- **Your chords in a row.** Each sits in its own window of the neck, with the strings lined up
  across the windows:
  - a note held from one chord to the next is a lime thread between them;
  - each window shows its starting fret ("5fr").
- **Choose where the hand plays** (the area of the neck) and which strings to use.
- **Click a chord to see other ways to play it,** closest first:
  - "Another way";
  - one-finger substitutions ("G becomes G/B: one finger moves");
  - a chord that could slip into a gap.
  You preview it, then keep it or go back.
- **Under the row, each change:** "Dm to G: 2 notes held, 3 semitones moved".
- **A tunings panel** suggests tunings that make the song easier.

## Rhythm

**The circle is the page.**
- It shows one loop, with the 1 at the top.
- Notes are dots. Big dots are accents, and held notes are arcs.
- Ticks show the counts, longer at the start of each group.
- The centre shows the gaps between notes ("3 3 2").
- Dots sit where they sound, so swing looks like it feels.
- Click any point to add or remove a note.

**Controls**
- Space taps and Enter plays or stops. There are no Play or Tap buttons, only small key hints
  that can also be clicked for mouse or touch.
- Clear is at the top left.
- Time signature, bpm and bars are at the top right, always visible.
- Taps keep their feel: swing is heard and shown, and never forced onto a grid.

**Subdivision**
- Named, not numbered: 8ths, triplets, 16ths, sextuplets.
- Only subdivisions that make sense for the time signature are offered, never "9 per beat".
- A change of subdivision must be audible.

**Ideas in three banners**

| Banner | Meaning |
|---|---|
| Grounded | Reinforces the spine and makes the time signature easy to feel. |
| Playful | Introduces displacement, syncopation or contrasting groupings without losing the underlying pulse. |
| Exploratory | Uses more unusual subdivisions, accents or rhythmic tension. |

- Clicking a banner opens a short list of its ideas.
- Each idea names its theory (tihai, polyrhythm, syncopation, canon…) and says in one line what
  it does to your rhythm.
- Click an idea to hear it with your spine, and click again to turn it off.
- An idea plays alongside your spine; it never rewrites it.

**Phrases**
- The loop can run as a phrase of several bars.
- Endings (a tihai, a fill) can play on the last bar only.
- A counter shows "bar 3 of 4".

**Theories to present**
- Tihai and other landing cadences.
- Polyrhythms (3 against 4).
- Syncopation.
- Call and response, and canon.
- Groupings across the bar.
- Subdivisions and swing.
- Spoken syllables: konnakol, takadimi and counting.

**Lessons from the last version**
- Polyrhythms must sound like a second voice against your spine, not a replacement for it.
- Too many controls at once buried the circle.
