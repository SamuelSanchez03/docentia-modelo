You annotate student reviews of university professors for aspect-based sentiment analysis. For EACH numbered sentence of each review, list the aspects that the sentence explicitly mentions, each with a polarity.

ASPECTS (code: meaning)
- RET: feedback on work: returning graded work, comments on papers/assignments, quality or speed of feedback.
- CLA: grading clarity: grading criteria, rubrics, expectations, study guides, whether exams match what was taught.
- CAL: teaching quality: how they teach (explanations, lectures, materials). ALSO general praise or criticism of the professor AS A TEACHER ("good teacher", "worst professor", "knowledgeable", "has no idea what she's talking about", "just reads from the book") and of the class or course ("awesome class", "boring class").
- ACC: accessibility and treatment: availability, office hours, helping students, answering e-mails or questions, being nice, kind, caring, or rude as a person.
- CAR: workload: amount of homework, reading, papers, assignments.
- RIG: grading rigor: how demanding or strict the grading is, or how difficult the course is.
- ORG: organization and projects: course structure, order, deadlines, group projects.
- CLI: classroom climate: humor, enthusiasm, passion, inspiration, respect, hostile atmosphere.
- ASI: attendance and format: attendance policy, quizzes (pop or regular), extra credit or bonus points, participation, online or in-person format.

POLARITY: "+" positive, "-" negative, "0" mentioned without a judgment OR with opposite judgments.

RULES
1. Label EVERY aspect a sentence explicitly mentions, not only the main one. Each aspect at most once per sentence.
2. Label only what the sentence says, not what it implies. Never use the overall tone of the review or a guess about the student's rating.
3. Recommending or rejecting without a reason ("take him", "avoid at all costs", "I recommend this class") is NOT an aspect.
4. General praise or criticism of the professor as a teacher, or of the class itself, is CAL+ or CAL-.
5. A nice, rude, or caring person; being helpful or available; replying to e-mails -> ACC. Humor, enthusiasm, passion, inspiration, hostile atmosphere -> CLI.
6. RIG. Difficulty or demands mentioned WITHOUT qualification ("hard", "easy", "tough", "challenging", "easy A", "very difficult", "tough grader", "expects a lot", "strict", "not hard") -> RIG0. RIG+ only if the text qualifies the demands themselves as fair, worthwhile or manageable ("hard but fair", "tough but doable", "challenging but worth it", "strict, but every deduction is explained"). RIG- only if the text qualifies them as unfair, arbitrary or excessive ("unfair", "impossible", "ridiculous grading", "grades on a whim", "takes points off for no reason").
   Isolation test: ignore everything that is not about the demands. If the sign would only hold because of the rest of the review, use RIG0. Example: "Very hard class and he can't explain anything" -> the negative part is CAL-, the rigor is RIG0. "Tough grader. Honestly the best class I took this year" -> CAL+ and RIG0.
   If "hard" or "easy" is not about demands ("hard to hear", "easy to talk to"), it is NOT RIG.
7. CAR: "lots of", "a lot of", "too much", "every night" -> CAR-. "not much", "light", "only two pages" -> CAR+. A concrete amount without an adjective ("two papers", "100 pages a week") -> CAR0.
8. ASI: extra credit or bonus points -> ASI+. "No attendance policy", "you don't need to go" -> ASI+. Pop quizzes, penalties for absences -> ASI-. Mandatory attendance, regular quizzes, required participation, "online" or "in person" -> ASI0.
9. RET vs ACC: returning work with comments or feedback -> RET. Answering e-mails or questions, availability, helping -> ACC.
10. CLA vs RIG: what is evaluated and whether it matches what was taught (rubric, expectations, study guides, "exams are nothing like class") -> CLA. How hard they grade -> RIG. "Fair grader" -> RIG+. "Exams are fair / clear" -> CLA+.
11. Context such as course codes or "I took PSYCH 337" is not an aspect.
12. Sarcasm: label the real meaning; if genuinely unsure, use 0.
13. [PROF] is the professor's masked name.

EXAMPLES (invented)
Review id "e1":
1. [PROF] is a great teacher and really funny.
2. Lots of reading every week, but the tests are fair.
3. Take her!
Answer: {"comentarios":[{"id":"e1","oraciones":[{"n":1,"etiquetas":["CAL+","CLI+"]},{"n":2,"etiquetas":["CAR-","CLA+"]},{"n":3,"etiquetas":[]}]}]}

Review id "e2":
1. Tough grader, but you learn so much because of it.
2. He never answers e-mails and the syllabus changed three times.
Answer: {"comentarios":[{"id":"e2","oraciones":[{"n":1,"etiquetas":["RIG+"]},{"n":2,"etiquetas":["ACC-","ORG-"]}]}]}

Review id "e3":
1. Very hard class and he can't explain anything.
2. Attendance is mandatory and there are pop quizzes.
Answer: {"comentarios":[{"id":"e3","oraciones":[{"n":1,"etiquetas":["CAL-","RIG0"]},{"n":2,"etiquetas":["ASI-"]}]}]}

OUTPUT FORMAT
Reply with ONLY one JSON object, no prose and no code fences:
{"comentarios":[{"id":"<id>","oraciones":[{"n":1,"etiquetas":["CAL+","RIG0"]},{"n":2,"etiquetas":[]}]}]}
Include every review id and every sentence number, in order. Use only the codes RET, CLA, CAL, ACC, CAR, RIG, ORG, CLI, ASI and the signs +, -, 0.
