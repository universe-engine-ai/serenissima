--- a/backend/ais/answertomessages.py
+++ b/backend/ais/answertomessages.py
@@ -209,7 +209,7 @@
         kinos_prompt = (
             f"You are {ai_display_name}, an AI citizen of Venice. You are responding to a message from {sender_display_name}.\n"
             f"IMPORTANT: Your response MUST be VERY SHORT, human-like, and conversational. "
-            f"Start your response with a very casual greeting, like 'Hey {sender_display_name},' or 'Ciao {sender_display_name},' or simply '{sender_display_name},'. "
+            f"Start your response with a very casual greeting, such as 'Hey {sender_display_name},' or 'Ciao {sender_display_name},'. "
             f"DO NOT use formal language, DO NOT write long paragraphs, DO NOT include any fluff or boilerplate. "
             f"Be direct, natural, and concise. Imagine you're sending a quick, informal message.\n\n"
             f"CRITICAL: Use the structured context provided in the 'addSystem' field (detailed below) to make your response RELEVANT to {sender_display_name} and FOCUSED ON GAMEPLAY. "
