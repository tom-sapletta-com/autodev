// This script will be executed when MongoDB starts for the first time
// It creates the initial admin user for RocketChat to bypass the setup wizard

db = db.getSiblingDB('rocketchat');

// Create the admin user if it doesn't exist
if (db.getCollection('users').countDocuments({ username: 'admin' }) === 0) {
  print('Creating admin user...');
  
  // Create admin user
  db.getCollection('users').insertOne({
    createdAt: new Date(),
    services: {
      password: {
        bcrypt: '$2a$10$n9CM8OgInDlwpvjLKLPML.eizXIzLlRtgCh3GRLafOdR9ldAUh/KG' // Hash for 'dxIsDLnhiqKfDt5J'
      }
    },
    username: 'admin',
    emails: [
      {
        address: 'admin@example.com',
        verified: true
      }
    ],
    type: 'user',
    status: 'online',
    active: true,
    roles: ['admin'],
    name: 'Administrator',
    _updatedAt: new Date(),
    settings: {
      preferences: {
        enableAutoAway: true,
        idleTimeLimit: 300,
        desktopNotifications: 'all',
        pushNotifications: 'all',
        unreadAlert: true
      }
    }
  });
  
  print('Admin user created successfully');
}

// Set the setup wizard as completed
if (db.getCollection('rocketchat_settings').countDocuments({ _id: 'Show_Setup_Wizard' }) === 0) {
  print('Setting up wizard as completed...');
  
  db.getCollection('rocketchat_settings').insertOne({
    _id: 'Show_Setup_Wizard',
    value: 'completed',
    type: 'string',
    public: true,
    createdAt: new Date(),
    _updatedAt: new Date()
  });
  
  print('Setup wizard marked as completed');
}

// Disable registration
if (db.getCollection('rocketchat_settings').countDocuments({ _id: 'Accounts_RegistrationForm' }) === 0) {
  print('Disabling registration...');
  
  db.getCollection('rocketchat_settings').insertOne({
    _id: 'Accounts_RegistrationForm',
    value: 'disabled',
    type: 'string',
    public: true,
    createdAt: new Date(),
    _updatedAt: new Date()
  });
  
  print('Registration disabled');
}

print('MongoDB initialization completed successfully');
