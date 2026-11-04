# Recording guide for the voice clone

Read the passage below once, in the voice you want in the film. Save it as `video/assets/voice/sample/aryan.mp3`. Then make the clone in the ElevenLabs page (Voices, Add a new voice, Instant Voice Clone) or with `uv run video/voice/generate_voice.py clone`.

## What ElevenLabs needs

Source: the ElevenLabs guide for Instant Voice Cloning, read on November 4, 2026.

| Item | Requirement |
|---|---|
| Length | 1 to 2 minutes is the recommended length. The minimum is 10 seconds in total. More than 3 minutes gives no gain and can make the clone less stable. |
| Files | The number of files does not matter. One file is fine. |
| Format | MP3 at 192 kbps or more. WAV gives no better clone and can fail at upload. |
| Speaker | One speaker. No music, no echo, no background noise. |
| Level | Between -23 dB and -18 dB RMS, with a true peak of -3 dB. A normal recording app does this by default. |
| Silence | No long gaps. The clone copies the pauses. |
| Tone | One consistent tone from start to end. The clone copies the delivery of the sample. |

The passage below is about 290 words. At a normal pace that is 100 to 120 seconds. It uses the names and the numbers of the film, so the clone hears them in your voice.

## Setup

1. Use a quiet room. Stop the fan and the air conditioner.
2. Hold the microphone or the phone at a fixed distance of about 15 cm. Do not move during the read.
3. Read at the pace and in the tone of the film: brisk, clear, and warm. Smile a little. The clone copies this.
4. If you make a mistake, keep calm, wait one second, and read the sentence again. One slip is fine. Do not stop the recording.
5. Do not add noise removal, compression, or reverb. Export as MP3, 192 kbps or more.

## Pronunciation

| Written | Say |
|---|---|
| Muse | "mews" |
| Jev | "jev", one syllable, rhymes with "rev" |
| MVTec | "M V Tec" |
| AUROC | "A U rock" |

## The passage

Hello. My name is Aryan Srivastava, and I am a machine learning engineer from India. I like to work at the edge of what is new: language models, vision models, and the small tools that make them useful in the real world.

Here is the idea behind my project, in plain words. Most AI models write before they answer. Ask one whether a bottle on a factory line is broken, and it writes a long explanation first, more than a thousand tokens, and that takes about eight seconds. On a production line, that is far too slow. The bottle is long gone.

So I built a model that does not write at all. It looks at the picture, reads a short description, and returns one number for each question: how sure it is. It does this in a single pass, in about forty-five milliseconds. If I stop it halfway, at layer thirteen of fifty-two, it still answers well in twenty-one milliseconds.

Why does the number matter? Because a probability you can trust is worth more than a confident guess. When the model says seventy percent, about seventy percent of those parts really are defective. That is what makes a threshold mean something.

I tested it on seventeen hundred and twenty-five images from fifteen products. It reached an AUROC of zero point nine six two, with a calibration error of zero point zero four five. The closed models from TypeSafe, Liquid, and Baseten landed below that, and every one of them was worse calibrated.

The code, the trained heads, and the demo page are open under Apache two point oh. You can try it today. Drop an image, type your questions, press Run, and read the numbers.

Thank you for your time, and I hope you enjoy the film.

## After the clone

1. Run `uv run video/voice/generate_voice.py voices` and copy the id of the new voice.
2. Put the id in `.env` as `ELEVENLABS_VOICE_ID`.
3. Run `uv run video/voice/generate_voice.py generate --speed 1.05`.
