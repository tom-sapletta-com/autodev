const WebSocket = require('ws');
const axios = require('axios');

// Konfiguracja
const config = {
  rocketChatUrl: 'http://localhost:3100',
  botUsername: 'heyken_bot',
  botPassword: 'heyken123',
  botAuthToken: null,
  botUserId: null,
  debug: true // Włącz debugowanie
};

// Funkcja do logowania debugowania
function debug(message, data) {
  if (config.debug) {
    console.log(`[DEBUG] ${message}`, data ? data : '');
  }
}

// Funkcja do logowania bota
async function loginBot() {
  try {
    const response = await axios.post(`${config.rocketChatUrl}/api/v1/login`, {
      user: config.botUsername,
      password: config.botPassword
    });

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

// Funkcja do połączenia z WebSocket
function connectToWebSocket() {
  // Prawidłowy format URL dla WebSocket RocketChat
  const wsUrl = `${config.rocketChatUrl.replace('http://', 'ws://')}/websocket`;
  console.log(`Łączenie z WebSocket: ${wsUrl}`);
  const ws = new WebSocket(wsUrl);

  ws.on('open', () => {
    console.log('Połączono z WebSocket');
    
    // Połączenie z serwerem
    ws.send(JSON.stringify({
      msg: 'connect',
      version: '1'
    }));
    
    // Logowanie po połączeniu
    setTimeout(() => {
      debug('Wysyłanie żądania logowania');
      ws.send(JSON.stringify({
        msg: 'method',
        method: 'login',
        id: 'login-' + Date.now(),
        params: [
          { token: config.botAuthToken }
        ]
      }));
    }, 1000);
  });

  ws.on('message', (data) => {
    try {
      const message = JSON.parse(data);
      debug('Otrzymano wiadomość:', message);

      // Odpowiedź na ping
      if (message.msg === 'ping') {
        ws.send(JSON.stringify({
          msg: 'pong'
        }));
        return;
      }

      // Obsługa błędów
      if (message.msg === 'failed') {
        console.error('Błąd połączenia WebSocket:', message);
        return;
      }

      // Potwierdzenie połączenia
      if (message.msg === 'connected') {
        console.log('Połączono z serwerem RocketChat, logowanie...');
        ws.send(JSON.stringify({
          msg: 'method',
          method: 'login',
          id: 'login-' + Date.now(),
          params: [
            { token: config.botAuthToken }
          ]
        }));
        return;
      }

      // Obsługa wyniku logowania
      if (message.msg === 'result' && message.id && message.id.startsWith('login-')) {
        if (message.result) {
          console.log('Zalogowano do WebSocket');
          
          // Subskrypcja do wiadomości bezpośrednich
          ws.send(JSON.stringify({
            msg: 'sub',
            id: 'sub-dm-' + Date.now(),
            name: 'stream-notify-user',
            params: [config.botUserId + '/message', false]
          }));
          
          // Subskrypcja do wiadomości w pokojach
          ws.send(JSON.stringify({
            msg: 'sub',
            id: 'sub-rooms-' + Date.now(),
            name: 'stream-room-messages',
            params: ['__my_messages__', false]
          }));
          
          console.log('Zasubskrybowano do wiadomości');
        } else {
          console.error('Błąd logowania do WebSocket:', message.error);
        }
        return;
      }

      // Obsługa przychodzących wiadomości
      if (message.msg === 'changed') {
        if (message.collection === 'stream-room-messages' && message.fields && message.fields.args && message.fields.args.length > 0) {
          const [roomEvent] = message.fields.args;
          
          // Ignoruj wiadomości wysłane przez bota
          if (roomEvent.u && roomEvent.u._id === config.botUserId) {
            return;
          }

          console.log(`Nowa wiadomość od ${roomEvent.u ? roomEvent.u.username : 'nieznanego użytkownika'} w pokoju ${roomEvent.rid}: ${roomEvent.msg}`);
          
          // Sprawdź, czy wiadomość zawiera @heyken_bot lub jest wiadomością prywatną
          if (roomEvent.msg && (roomEvent.msg.includes('@heyken_bot') || roomEvent.t === 'd')) {
            const response = generateResponse(roomEvent.msg, roomEvent.u ? roomEvent.u.username : 'użytkowniku');
            sendMessage(roomEvent.rid, response);
          }
        }
      }
    } catch (error) {
      console.error('Błąd przetwarzania wiadomości WebSocket:', error);
    }
  });

  ws.on('error', (error) => {
    console.error('Błąd WebSocket:', error);
  });

  ws.on('close', () => {
    console.log('Połączenie WebSocket zamknięte. Ponowne połączenie za 5 sekund...');
    setTimeout(connectToWebSocket, 5000);
  });

  return ws;
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
    // Połączenie z WebSocket
    connectToWebSocket();
  } else {
    console.error('Nie można uruchomić bota bez zalogowania.');
    process.exit(1);
  }
}

// Uruchomienie bota
main();
