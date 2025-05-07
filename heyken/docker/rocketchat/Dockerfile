FROM registry.rocket.chat/rocketchat/rocket.chat:7.5.1

LABEL maintainer="Heyken System <admin@hey-ken.com>"

# Ekspozycja portów
EXPOSE 3000

# Zmienne środowiskowe
ENV ROOT_URL=http://localhost:3100 \
    PORT=3000 \
    MONGO_URL=mongodb://mongodb:27017/rocketchat \
    MONGO_OPLOG_URL=mongodb://mongodb:27017/local \
    MAIL_URL=smtp://smtp.gmail.com:465 \
    HTTP_FORWARDED_COUNT=1 \
    # Skip setup wizard
    OVERWRITE_SETTING_Show_Setup_Wizard=completed \
    # Admin user configuration
    ADMIN_USERNAME=admin \
    ADMIN_PASS=dxIsDLnhiqKfDt5J \
    ADMIN_EMAIL=admin@heyken.local \
    # Disable registration and require admin for new users
    OVERWRITE_SETTING_Accounts_RegistrationForm=disabled \
    OVERWRITE_SETTING_Accounts_ManuallyApproveNewUsers=true

# Uruchomienie Rocket.Chat
CMD ["node", "main.js"]
