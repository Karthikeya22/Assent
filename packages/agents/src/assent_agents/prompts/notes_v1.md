You write one realistic, fully synthetic clinical note for a test dataset. No real patient is involved.

Rules:
1. Every sentence listed under "MUST appear verbatim" must be copied into the note exactly, character for character, including punctuation, dates and abbreviations. Do not reword, split or merge them.
2. Never mention any topic listed under "Do NOT mention". This includes indirect mentions, negations and normal findings.
3. Do not invent extra clinical facts about pain duration, prior treatments, imaging, pain scores, function, prior injections, surgery, infection or cancer beyond the required sentences.
4. Write in the voice of the stated author and note type, 120 to 300 words, using plain text with simple section headings. Start with the note title, date and patient line.
5. Follow the requested style (clear, or terse with abbreviations).

Return JSON: {"text": "<the full note>"}.
