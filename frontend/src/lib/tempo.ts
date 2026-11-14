// Musical tempo terms for speaking pace, so a talk can be marked like a score.
// Italian tempo words are used in every language, as on printed music.

export function tempoMarking(wpm: number): string {
  if (wpm < 100) return 'Adagio'
  if (wpm < 120) return 'Andante'
  if (wpm < 150) return 'Moderato'
  if (wpm < 170) return 'Allegro'
  if (wpm < 190) return 'Vivace'
  return 'Presto'
}
