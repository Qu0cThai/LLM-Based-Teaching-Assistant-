def mcq_prompt(context, count, reason="", subject="General", difficulty="Medium"):
    return f"""
      You are an expert teaching assistant for the subject: "{subject}".
      Generate exactly {count} MCQs in STRICT JSON format.

      CRITICAL INSTRUCTION: The difficulty level of these questions MUST be strictly set to: {difficulty.upper()}.
      - If Easy: Focus on basic definitions, direct facts, and simple recognition.
      - If Medium: Focus on application, understanding, and connecting concepts.
      - If Hard: Focus on complex synthesis, critical thinking, exceptions, and deep analysis.
      
      STRICT RULES (CRITICAL):
      1. YOU MUST ONLY USE THE PROVIDED CONTEXT. DO NOT USE EXTERNAL KNOWLEDGE.
      2. If the correct answer is NOT explicitly stated or logically deduced ONLY from the text, DO NOT generate the question.
      3. The options must be plausible but only one can be definitively correct based on the text.
      4. CORE ACADEMIC CONCEPTS ONLY: Ask ONLY about the primary educational subject matter of the text (e.g., theories, definitions, formulas, historical events, mechanisms). NEVER ask about document metadata, the author's background, book preface, acknowledgments, or publication history.
      5. MAXIMUM DIVERSITY: Focus on completely different concepts. Do NOT generate multiple questions about the same specific topic or entity. Every question must test a distinct piece of knowledge.
      6. LOGICAL COHERENCE: Do not mix unrelated concepts together just because they are in the same text.
      
      Previous attempts were rejected because:
      {reason}

      FOR EACH QUESTION:
      - Provide a ONE-SENTENCE justification explaining why the correct answer is correct BASED ONLY ON THE CONTEXT.

      RULES:
      - 4 options A–D
      - answer must be one of A, B, C, D

      JSON FORMAT:
      [
        {{
          "question": "...",
          "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
          "answer": "B",
          "justification": "..."
        }}
      ]

      Context:
      {context}
      """

def short_answer_prompt(context, n, reason="", subject="General", difficulty="Medium"):
    return f"""
      You are an expert teaching assistant for the subject: "{subject}".
      Generate exactly {n} DIFFERENT SHORT ANSWER questions.

      CRITICAL INSTRUCTION: The difficulty level MUST be {difficulty.upper()}. Adapt the complexity of the question to match this level.
      
      STRICT RULES (CRITICAL):
      1. STRICTLY NO OUTSIDE KNOWLEDGE. Use ONLY the text provided.
      2. CORE ACADEMIC CONCEPTS ONLY: Ask ONLY about the primary educational subject matter of the text (e.g., theories, definitions, formulas, historical events, mechanisms). NEVER ask about document metadata, the author's background, book preface, acknowledgments, or publication history.
      3. MAXIMUM DIVERSITY: Focus on completely different concepts, definitions, causes, or mechanics. Do NOT ask variations of the same question or test the same entity twice.
      4. LOGICAL COHERENCE: Do NOT mix unrelated topics together. Keep the question focused on a single logical concept.
      5. EXPLICIT GROUNDING: Your answer MUST heavily use vocabulary, terms, and phrasing directly from the text to explain the concept.
      6. Answer length: 15–35 words.

      CRITICAL INSTRUCTION: Do not paraphrase. You must extract the answer DIRECTLY from the provided text using exact phrasing and verbatim quotes wherever possible. The answer must physically appear in the text.
      
      Previous attempts were rejected because:
      {reason}

      JSON ONLY:
      [
        {{
          "type": "short_answer",
          "question": "...",
          "answer": "...",
          "justification": "..."
        }}
      ]

      Context:
      {context}
      """

def fill_blank_prompt(context, n, reason="", subject="General", difficulty="Medium"):
    return f"""
      You are an expert teaching assistant for the subject: "{subject}".
      Generate exactly {n} FILL IN THE BLANK questions.

      CRITICAL INSTRUCTION: The difficulty level MUST be {difficulty.upper()}. 
      - If Easy: Blank out simple, obvious vocabulary.
      - If Hard: Blank out nuanced, highly specific academic terminology.
      
      STRICT RULES (CRITICAL):
      1. EXACT EXTRACTION (NO PARAPHRASING): You MUST extract a complete, verbatim sentence directly from the provided text. Do not rewrite, change words, or summarize it.
      2. THE BLANK: Replace exactly ONE important academic term (1-3 words) in that sentence with exactly four underscores "____". The removed word(s) will be the answer.
      3. CORE ACADEMIC CONCEPTS ONLY: Ask ONLY about the primary educational subject matter. NEVER create blanks for document metadata, author names, publication years, or section numbers.
      4. MAXIMUM DIVERSITY: Focus on completely different concepts. Do NOT generate multiple questions about the same specific topic.
      5. DO NOT COPY THE EXAMPLE: You must generate entirely new questions based ONLY on the provided Context.

      Previous attempts were rejected because:
      {reason}

      JSON ONLY FORMAT EXAMPLE (DO NOT COPY THIS):
      [
        {{
          "type": "fill_blank",
          "question": "The powerhouse of the cell is the ____.",
          "answer": "mitochondria"
        }}
      ]

      Context:
      {context}
      """

def judge_prompt(q_text, options, answer, context):
    return f"""
      You are an expert strict evaluator (LLM Judge).
      Evaluate if the following Multiple Choice Question is valid based STRICTLY on the provided context.

      Context:
      {context}

      Question: {q_text}
      Options: {options}
      Declared Answer: {answer}

      Evaluation Criteria:
      1. Does the question and the correct answer rely ONLY on the context? (No outside knowledge).
      2. Are the 3 incorrect options (distractors) plausible but definitively wrong according to the text?
      3. Is the question free of hallucinations?
      4. Does the question ask about actual domain knowledge? (If it asks about document structure, section IDs, document metadata, the author's background, or the book's preface, it is INVALID).
      5. Logical Coherence: Does the relationship between the question and the answer make logical sense in the real world? (e.g., if the question mixes unrelated topics purely by accident, it is INVALID).

      If ALL criteria are met, output ONLY the word: VALID
      If ANY criterion fails, output ONLY the word: INVALID
      """