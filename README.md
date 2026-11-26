# osesp-monitor

Vigia a página do Recital de Encerramento de Semestre da Academia de Música da Osesp
(Sala São Paulo, 04/12/2026) a cada 5 minutos via GitHub Actions e avisa quando
o botão "Ingresso em breve" mudar.

- Aviso: WhatsApp (CallMeBot) e/ou Telegram, se os Secrets existirem, + issue no GitHub (e-mail).
- Mensagem diária às 9h (Brasília) confirmando que o monitor está ativo.
- Depois de avisar, ou depois de 04/12, o workflow se desliga sozinho.
- Teste manual: Actions > Monitor Osesp > Run workflow (mode = test).
