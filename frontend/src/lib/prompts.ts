// Practice prompts per mode and language. Picked at random on the Live and Upload pages.
import type { Lang, SessionMode } from '../api/client'

export type PromptMode = 'impromptu' | 'elevator_pitch' | 'interview' | 'table_topics'

export const PROMPT_MODES: PromptMode[] = ['impromptu', 'elevator_pitch', 'interview', 'table_topics']

export function isPromptMode(m: SessionMode): m is PromptMode {
  return (PROMPT_MODES as SessionMode[]).includes(m)
}

/** Length choices in seconds per mode; the first is the default. */
export const MODE_TARGETS: Partial<Record<SessionMode, number[]>> = {
  timed_pitch: [60, 180, 300],
  impromptu: [60, 120],
  elevator_pitch: [30, 60],
  interview: [120, 300, 600],
  table_topics: [120],
}

/** Seconds to think before recording starts, per mode. */
export const PREP_SECONDS: Partial<Record<SessionMode, number>> = {
  impromptu: 30,
  elevator_pitch: 15,
  table_topics: 0,
  interview: 0,
}

/**
 * Timing lights (green, amber, red) as seconds into the talk. Table Topics follows the
 * Toastmasters rule: green at 1:00, amber at 1:30, red at 2:00. Other modes use
 * 50 %, 75 % and 100 % of the target.
 */
export function timingLights(mode: SessionMode, target: number | null): [number, number, number] | null {
  if (!target) return null
  if (mode === 'table_topics') return [60, 90, 120]
  return [target * 0.5, target * 0.75, target]
}

export function lightAt(lights: [number, number, number] | null, elapsed: number): 'none' | 'green' | 'amber' | 'red' {
  if (!lights) return 'none'
  if (elapsed >= lights[2]) return 'red'
  if (elapsed >= lights[1]) return 'amber'
  if (elapsed >= lights[0]) return 'green'
  return 'none'
}

const BANK: Record<PromptMode, Record<Lang, string[]>> = {
  impromptu: {
    en: [
      'The best advice you have ever received',
      'A skill everyone should learn before 25',
      'Should cities ban cars from their centres?',
      'A place that changed how you see the world',
      'What makes a good team?',
      'Is it better to be a specialist or a generalist?',
      'The most underrated invention',
      'A small habit that made a big difference',
      'Should homework be abolished?',
      'What would you do with one extra hour every day?',
      'A mistake you learned the most from',
      'Why people should read more fiction',
    ],
    de: [
      'Der beste Rat, den du je bekommen hast',
      'Eine Fähigkeit, die jeder vor 25 lernen sollte',
      'Sollten Städte Autos aus der Innenstadt verbannen?',
      'Ein Ort, der deinen Blick auf die Welt verändert hat',
      'Was macht ein gutes Team aus?',
      'Ist es besser, Spezialist oder Generalist zu sein?',
      'Die am meisten unterschätzte Erfindung',
      'Eine kleine Gewohnheit mit großer Wirkung',
      'Sollten Hausaufgaben abgeschafft werden?',
      'Was würdest du mit einer zusätzlichen Stunde pro Tag machen?',
      'Ein Fehler, aus dem du am meisten gelernt hast',
      'Warum Menschen mehr Romane lesen sollten',
    ],
    ur: [
      'سب سے اچھا مشورہ جو آپ کو کبھی ملا',
      'ایک ہنر جو ہر کسی کو 25 سال سے پہلے سیکھنا چاہیے',
      'کیا شہروں کے مرکز میں گاڑیوں پر پابندی ہونی چاہیے؟',
      'ایک جگہ جس نے دنیا کو دیکھنے کا آپ کا انداز بدل دیا',
      'ایک اچھی ٹیم کیا بناتی ہے؟',
      'ماہر ہونا بہتر ہے یا ہر فن مولا؟',
      'سب سے کم سراہی جانے والی ایجاد',
      'ایک چھوٹی سی عادت جس نے بڑا فرق ڈالا',
      'کیا ہوم ورک ختم کر دینا چاہیے؟',
      'اگر روزانہ ایک گھنٹہ زیادہ ملے تو آپ کیا کریں گے؟',
      'ایک غلطی جس سے آپ نے سب سے زیادہ سیکھا',
      'لوگوں کو زیادہ کہانیاں اور ناول کیوں پڑھنے چاہییں',
    ],
  },
  elevator_pitch: {
    en: [
      'Introduce yourself to a recruiter at a career fair',
      'Pitch your current project to a potential investor',
      'Explain what you do to someone outside your field',
      'Pitch an app idea that solves an everyday problem',
      'Convince a new colleague to join your side project',
      'Introduce your team to a new client',
    ],
    de: [
      'Stell dich einer Recruiterin auf einer Karrieremesse vor',
      'Pitche dein aktuelles Projekt einem möglichen Investor',
      'Erkläre jemandem außerhalb deines Fachs, was du machst',
      'Pitche eine App-Idee, die ein Alltagsproblem löst',
      'Überzeuge eine neue Kollegin, bei deinem Nebenprojekt mitzumachen',
      'Stelle dein Team einem neuen Kunden vor',
    ],
    ur: [
      'کیریئر فیئر میں ایک ریکروٹر سے اپنا تعارف کروائیں',
      'اپنا موجودہ پروجیکٹ کسی ممکنہ سرمایہ کار کے سامنے پیش کریں',
      'کسی دوسرے شعبے کے فرد کو سمجھائیں کہ آپ کیا کام کرتے ہیں',
      'روزمرہ کا مسئلہ حل کرنے والی ایک ایپ کا آئیڈیا پیش کریں',
      'ایک نئے ساتھی کو اپنے سائیڈ پروجیکٹ میں شامل ہونے پر قائل کریں',
      'ایک نئے کلائنٹ سے اپنی ٹیم کا تعارف کروائیں',
    ],
  },
  interview: {
    en: [
      'Tell me about yourself.',
      'Why do you want this role?',
      'Describe a time you handled a conflict at work.',
      'What is your greatest strength, and a weakness you are working on?',
      'Tell me about a project you are proud of.',
      'Describe a time you failed and what you learned.',
      'Where do you see yourself in five years?',
      'How do you handle tight deadlines?',
      'Tell me about a time you led without formal authority.',
      'Why should we hire you?',
      'Describe a difficult decision you made with incomplete information.',
      'Do you have any questions for us?',
    ],
    de: [
      'Erzählen Sie etwas über sich.',
      'Warum möchten Sie diese Stelle?',
      'Beschreiben Sie, wie Sie einen Konflikt im Job gelöst haben.',
      'Was ist Ihre größte Stärke, und an welcher Schwäche arbeiten Sie?',
      'Erzählen Sie von einem Projekt, auf das Sie stolz sind.',
      'Beschreiben Sie ein Scheitern und was Sie daraus gelernt haben.',
      'Wo sehen Sie sich in fünf Jahren?',
      'Wie gehen Sie mit knappen Fristen um?',
      'Erzählen Sie, wie Sie ohne formale Autorität geführt haben.',
      'Warum sollten wir Sie einstellen?',
      'Beschreiben Sie eine schwierige Entscheidung mit unvollständigen Informationen.',
      'Haben Sie Fragen an uns?',
    ],
    ur: [
      'اپنے بارے میں کچھ بتائیں۔',
      'آپ یہ عہدہ کیوں چاہتے ہیں؟',
      'کام پر کسی اختلاف کو سنبھالنے کا کوئی واقعہ بیان کریں۔',
      'آپ کی سب سے بڑی خوبی کیا ہے، اور کس کمزوری پر آپ کام کر رہے ہیں؟',
      'کسی ایسے پروجیکٹ کے بارے میں بتائیں جس پر آپ کو فخر ہے۔',
      'کسی ناکامی کا ذکر کریں اور بتائیں کہ آپ نے اس سے کیا سیکھا۔',
      'آپ خود کو پانچ سال بعد کہاں دیکھتے ہیں؟',
      'آپ کم وقت میں کام مکمل کرنے کا دباؤ کیسے سنبھالتے ہیں؟',
      'بتائیں جب آپ نے کسی باقاعدہ اختیار کے بغیر قیادت کی۔',
      'ہم آپ کو کیوں منتخب کریں؟',
      'نامکمل معلومات کے ساتھ کیا گیا کوئی مشکل فیصلہ بیان کریں۔',
      'کیا آپ ہم سے کچھ پوچھنا چاہتے ہیں؟',
    ],
  },
  table_topics: {
    en: [
      'If you could have dinner with anyone, who would it be and why?',
      'Describe your perfect weekend.',
      'What is something you changed your mind about?',
      'If you could master any instrument overnight, which one?',
      'Tell us about a teacher who made a difference.',
      'What would you put in a time capsule for 2050?',
      'Is it ever right to break a rule?',
      'Describe a smell that brings back a memory.',
      'What is the most useful thing you own?',
      'If you could live in any decade, which would you pick?',
    ],
    de: [
      'Mit wem würdest du gern zu Abend essen und warum?',
      'Beschreibe dein perfektes Wochenende.',
      'Bei welchem Thema hast du deine Meinung geändert?',
      'Welches Instrument würdest du gern über Nacht beherrschen?',
      'Erzähl von einer Lehrerin oder einem Lehrer, die oder der etwas bewegt hat.',
      'Was würdest du in eine Zeitkapsel für 2050 legen?',
      'Ist es jemals richtig, eine Regel zu brechen?',
      'Beschreibe einen Geruch, der eine Erinnerung weckt.',
      'Was ist der nützlichste Gegenstand, den du besitzt?',
      'In welchem Jahrzehnt würdest du gern leben?',
    ],
    ur: [
      'اگر آپ کسی کے ساتھ بھی کھانا کھا سکیں تو وہ کون ہوگا اور کیوں؟',
      'اپنی بہترین ہفتہ وار چھٹی کا حال بیان کریں۔',
      'کس بات پر آپ نے اپنی رائے بدلی؟',
      'اگر آپ راتوں رات کوئی ساز سیکھ سکیں تو کون سا؟',
      'کسی استاد کے بارے میں بتائیں جنہوں نے آپ کی زندگی بدلی۔',
      'آپ 2050 کے لیے ٹائم کیپسول میں کیا رکھیں گے؟',
      'کیا کبھی کوئی اصول توڑنا درست ہوتا ہے؟',
      'کوئی ایسی خوشبو بیان کریں جو آپ کو کوئی یاد دلاتی ہے۔',
      'آپ کی سب سے کارآمد چیز کون سی ہے؟',
      'اگر آپ کسی بھی دہائی میں رہ سکیں تو کون سی چنیں گے؟',
    ],
  },
}

export function promptBank(mode: PromptMode, lang: Lang): string[] {
  return BANK[mode][lang]
}

/** A random prompt from the bank, different from `current` when possible. */
export function randomPrompt(mode: PromptMode, lang: Lang, current?: string, rand = Math.random): string {
  const options = BANK[mode][lang].filter((p) => p !== current)
  return options[Math.floor(rand() * options.length)] ?? BANK[mode][lang][0]
}
