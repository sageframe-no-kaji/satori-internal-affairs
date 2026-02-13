# Internal Affairs

**Player-facing frontend for the medical mystery simulator.**

Internal Affairs is the SvelteKit web application that presents the investigative interface to players. It communicates with the Satori backend to submit actions, receive case state updates, and render the investigation UI. This layer does NOT contain game logic, generate cases, or manage LLM interactions — it is purely the presentation and interaction layer.
