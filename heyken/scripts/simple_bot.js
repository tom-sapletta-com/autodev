const axios = require('axios');

// Konfiguracja
const config = {
  rocketChatUrl: 'http://localhost:3100',
  botUsername: 'heyken_bot',
  botPassword: 'heyken123',
  botAuthToken: null,
  botUserId: null,
  pollInterval: 2000, // Sprawdzanie nowych wiadomości co 2 sekundy
  debug: true
};

// Zmienne globalne
let lastTimestamp = new Date();
let directMessageRooms = [];
let channelRooms = [];

// Funkcja do logowania debugowania
function debug(message, data) {
  if (config.debug) {
    console.log(`[DEBUG] ${message}`, data ? data : '');
  }
}

// Funkcja do logowania bota
async function loginBot() {
  try {
    console.log(`Logowanie jako ${config.botUsername}...`);
    console.log(`URL: ${config.rocketChatUrl}/api/v1/login`);
    
    // Sprawdź, czy serwer RocketChat jest dostępny
    try {
      const pingResponse = await axios.get(`${config.rocketChatUrl}/api/info`);
      console.log('Serwer RocketChat jest dostępny:', pingResponse.status);
    } catch (pingError) {
      console.error('Serwer RocketChat nie jest dostępny:', pingError.message);
      console.error('Sprawdź, czy RocketChat działa na adresie:', config.rocketChatUrl);
      return false;
    }
    
    // Próba logowania
    const response = await axios.post(`${config.rocketChatUrl}/api/v1/login`, {
      user: config.botUsername,
      password: config.botPassword
    });

    console.log('Odpowiedź serwera:', JSON.stringify(response.data, null, 2));

    if (response.data && response.data.status === 'success') {
      config.botAuthToken = response.data.data.authToken;
      config.botUserId = response.data.data.userId;
      console.log(`Bot zalogowany pomyślnie. User ID: ${config.botUserId}`);
      return true;
    } else {
      console.error('Błąd logowania bota:', response.data);
      return false;
    }
  } catch (error) {
    console.error('Błąd podczas logowania bota:', error.message);
    if (error.response) {
      console.error('Dane odpowiedzi:', error.response.data);
      console.error('Status odpowiedzi:', error.response.status);
      console.error('Nagłówki odpowiedzi:', error.response.headers);
    } else if (error.request) {
      console.error('Żądanie zostało wysłane, ale nie otrzymano odpowiedzi');
      console.error(error.request);
    } else {
      console.error('Błąd podczas konfiguracji żądania:', error.message);
    }
    return false;
  }
}

// Funkcja do pobierania pokojów, w których jest bot
async function getRooms() {
  try {
    // Pobierz wiadomości bezpośrednie (DM)
    const dmResponse = await axios.get(`${config.rocketChatUrl}/api/v1/im.list`, {
      headers: {
        'X-Auth-Token': config.botAuthToken,
        'X-User-Id': config.botUserId
      }
    });

    if (dmResponse.data && dmResponse.data.success) {
      directMessageRooms = dmResponse.data.ims;
      console.log(`Pobrano ${directMessageRooms.length} pokojów wiadomości bezpośrednich`);
    }

    // Pobierz kanały, w których jest bot
    const channelsResponse = await axios.get(`${config.rocketChatUrl}/api/v1/channels.list.joined`, {
      headers: {
        'X-Auth-Token': config.botAuthToken,
        'X-User-Id': config.botUserId
      }
    });

    if (channelsResponse.data && channelsResponse.data.success) {
      channelRooms = channelsResponse.data.channels;
      console.log(`Pobrano ${channelRooms.length} kanałów`);
    }

    return true;
  } catch (error) {
    console.error('Błąd podczas pobierania pokojów:', error.message);
    return false;
  }
}

// Funkcja do wysyłania wiadomości
async function sendMessage(roomId, text) {
  try {
    const response = await axios.post(
      `${config.rocketChatUrl}/api/v1/chat.postMessage`,
      {
        roomId,
        text
      },
      {
        headers: {
          'X-Auth-Token': config.botAuthToken,
          'X-User-Id': config.botUserId
        }
      }
    );

    if (response.data && response.data.success) {
      console.log(`Wiadomość wysłana do pokoju ${roomId}`);
      return true;
    } else {
      console.error('Błąd wysyłania wiadomości:', response.data);
      return false;
    }
  } catch (error) {
    console.error('Błąd podczas wysyłania wiadomości:', error.message);
    return false;
  }
}

// Funkcja do sprawdzania nowych wiadomości w pokoju
async function checkRoomMessages(roomId, roomType, roomName) {
  try {
    const endpoint = roomType === 'direct' ? 'im.messages' : 'channels.messages';
    const params = {
      roomId,
      count: 10 // Pobierz ostatnie 10 wiadomości
    };

    const response = await axios.get(`${config.rocketChatUrl}/api/v1/${endpoint}`, {
      headers: {
        'X-Auth-Token': config.botAuthToken,
        'X-User-Id': config.botUserId
      },
      params
    });

    if (response.data && response.data.success) {
      const messages = response.data.messages;
      
      // Sprawdź, czy są nowe wiadomości (nowsze niż ostatnie sprawdzenie)
      const newMessages = messages.filter(msg => {
        const msgDate = new Date(msg.ts);
        return msgDate > lastTimestamp && msg.u._id !== config.botUserId;
      });

      if (newMessages.length > 0) {
        console.log(`Znaleziono ${newMessages.length} nowych wiadomości w pokoju ${roomName || roomId}`);
        
        // Odpowiedz na każdą nową wiadomość
        for (const msg of newMessages) {
          const username = msg.u.username;
          const messageText = msg.msg;
          
          console.log(`Nowa wiadomość od ${username} w pokoju ${roomName || roomId}: ${messageText}`);
          
          // Sprawdź, czy wiadomość zawiera @heyken_bot lub jest wiadomością prywatną
          if (messageText.includes('@heyken_bot') || roomType === 'direct') {
            const response = generateResponse(messageText, username);
            await sendMessage(roomId, response);
          }
        }
      }
    }
  } catch (error) {
    console.error(`Błąd podczas sprawdzania wiadomości w pokoju ${roomId}:`, error.message);
  }
}

// Funkcja do sprawdzania wszystkich pokojów
async function checkAllRooms() {
  // Sprawdź wiadomości bezpośrednie
  for (const room of directMessageRooms) {
    await checkRoomMessages(room._id, 'direct', room.usernames.filter(u => u !== config.botUsername).join(', '));
  }

  // Sprawdź kanały
  for (const channel of channelRooms) {
    await checkRoomMessages(channel._id, 'channel', channel.name);
  }

  // Aktualizuj znacznik czasu ostatniego sprawdzenia
  lastTimestamp = new Date();
}

// Funkcja do generowania odpowiedzi
function generateResponse(message, username) {
  // Usuwamy @heyken_bot z wiadomości, jeśli występuje
  const cleanMessage = message.replace('@heyken_bot', '').trim().toLowerCase();
  
  // Proste odpowiedzi na podstawie zawartości wiadomości
  if (cleanMessage.includes('cześć') || cleanMessage.includes('czesc') || cleanMessage.includes('hej') || cleanMessage.includes('witaj')) {
    return `Cześć @${username}! W czym mogę pomóc?`;
  }
  
  if (cleanMessage.includes('jak się masz') || cleanMessage.includes('jak sie masz')) {
    return `Dziękuję @${username}, mam się dobrze! Jestem gotowy do pomocy.`;
  }
  
  if (cleanMessage.includes('pomoc') || cleanMessage.includes('pomocy')) {
    return `@${username}, jestem Heyken Bot. Mogę odpowiadać na proste pytania i pomagać w podstawowych zadaniach. Jestem częścią systemu Heyken.`;
  }
  
  if (cleanMessage.includes('dziękuję') || cleanMessage.includes('dziekuje') || cleanMessage.includes('dzięki') || cleanMessage.includes('dzieki')) {
    return `Nie ma za co, @${username}! Zawsze do usług.`;
  }
  
  // Domyślna odpowiedź, jeśli nie pasuje do żadnego wzorca
  return `@${username}, otrzymałem twoją wiadomość. Jestem prostym botem i nadal się uczę. Czy mogę jakoś pomóc?`;
}

// Główna funkcja
async function main() {
  // Logowanie bota
  const loggedIn = await loginBot();
  
  if (loggedIn) {
    // Pobierz pokoje, w których jest bot
    await getRooms();
    
    // Uruchom pętlę sprawdzania wiadomości
    console.log(`Bot uruchomiony i nasłuchuje wiadomości (sprawdzanie co ${config.pollInterval/1000} sekund)...`);
    
    // Ustaw interwał sprawdzania wiadomości
    setInterval(async () => {
      await checkAllRooms();
    }, config.pollInterval);
  } else {
    console.error('Nie można uruchomić bota bez zalogowania.');
    process.exit(1);
  }
}

// Uruchomienie bota
main();
