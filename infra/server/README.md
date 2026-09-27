# Configuração do Backup Automatizado no Servidor (Raspberry Pi / Linux)

Este diretório contém os arquivos de serviço do **Systemd** para agendar o backup diário com **Rclone** e sincronização para o **Google Drive**.

---

## 1. Pré-requisitos no Servidor

1. **Rclone instalado e configurado:**
   - Verifique se o remote do Google Drive está funcionando:
     ```bash
     rclone lsd gdrive:
     ```
   - Caso o nome do seu remote seja diferente de `gdrive:`, defina a variável `RCLONE_REMOTE` no arquivo `.env` do projeto:
     ```env
     RCLONE_REMOTE=meu_remote:flauzino-backups
     ```

2. **Permissões do usuário:**
   - O usuário configurado no serviço (ex: `flauzino`) deve pertencer ao grupo `docker`:
     ```bash
     sudo usermod -aG docker $USER
     ```

3. **Notificações no Telegram (Opcional):**
   - No arquivo `.env`, preencha:
     ```env
     TELEGRAM_BOT_TOKEN="seu_token"
     TELEGRAM_CHAT_ID="seu_chat_id_numerico"
     ```

---

## 2. Instalação do Serviço e Timer

1. **Copie os arquivos de serviço para o diretório do Systemd:**
   ```bash
   sudo cp infra/server/flauzino-backup.service /etc/systemd/system/
   sudo cp infra/server/flauzino-backup.timer /etc/systemd/system/
   ```

2. **Ajuste o caminho e usuário se necessário:**
   - Verifique se o diretório do projeto e usuário em `/etc/systemd/system/flauzino-backup.service` correspondem ao seu ambiente:
     ```bash
     sudo nano /etc/systemd/system/flauzino-backup.service
     ```

3. **Recarregue o systemd e ative o timer:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now flauzino-backup.timer
   ```

4. **Verifique se o timer está ativo:**
   ```bash
   systemctl list-timers --all | grep flauzino
   ```

---

## 3. Teste Manual e Verificação de Logs

Para testar o backup imediatamente sem esperar as 03:00:
```bash
sudo systemctl start flauzino-backup.service
```

Acompanhe os logs em tempo real:
```bash
journalctl -u flauzino-backup.service -f
```
