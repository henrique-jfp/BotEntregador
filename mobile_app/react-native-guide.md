# 🚀 Entregador React Native App

Aplicativo nativo completo para controle pessoal de entregas.

## 📱 Setup Rápido

```bash
# Instalar React Native CLI
npm install -g react-native-cli

# Criar projeto
npx react-native init EntregadorApp
cd EntregadorApp

# Instalar dependências principais
npm install @react-navigation/native @react-navigation/stack
npm install react-native-screens react-native-safe-area-context
npm install react-native-image-picker react-native-maps
npm install react-native-geolocation-service
npm install @react-native-async-storage/async-storage
npm install react-native-push-notification

# iOS
cd ios && pod install && cd ..

# Executar
npx react-native run-android
npx react-native run-ios
```

## 🏗️ Estrutura do Projeto

```
src/
├── components/          # Componentes reutilizáveis
│   ├── Camera/         # Componente de câmera
│   ├── Map/            # Mapa e navegação
│   ├── DeliveryCard/   # Card de entrega
│   └── common/         # Botões, inputs, etc
├── screens/            # Telas do app
│   ├── HomeScreen/     # Tela inicial
│   ├── CameraScreen/   # Captura de fotos
│   ├── RouteScreen/    # Rota otimizada
│   ├── NavigationScreen/ # Navegação GPS
│   ├── GainsScreen/    # Controle de ganhos
│   └── ConfigScreen/   # Configurações
├── services/           # Lógica de negócio
│   ├── OCRService.js   # Processamento OCR
│   ├── RouteService.js # Otimização de rotas
│   ├── StorageService.js # Armazenamento local
│   └── APIService.js   # Comunicação com backend
├── utils/             # Utilitários
└── assets/            # Imagens, ícones, etc
```

## 🔧 Componentes Principais

### HomeScreen.js
```jsx
import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { launchImageLibrary } from 'react-native-image-picker';
import OCRService from '../services/OCRService';

const HomeScreen = ({ navigation }) => {
  const [photos, setPhotos] = useState([]);
  const [addresses, setAddresses] = useState([]);

  const pickImages = () => {
    const options = {
      mediaType: 'photo',
      selectionLimit: 8,
      quality: 0.8
    };

    launchImageLibrary(options, (response) => {
      if (response.assets) {
        setPhotos(response.assets);
      }
    });
  };

  const processPhotos = async () => {
    try {
      const extractedAddresses = await OCRService.extractAddresses(photos);
      setAddresses(extractedAddresses);
      navigation.navigate('Route', { addresses: extractedAddresses });
    } catch (error) {
      console.error('Erro no processamento:', error);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>📦 Entregador</Text>
      
      <TouchableOpacity style={styles.button} onPress={pickImages}>
        <Text style={styles.buttonText}>📸 Selecionar Fotos</Text>
      </TouchableOpacity>

      {photos.length > 0 && (
        <TouchableOpacity style={styles.processButton} onPress={processPhotos}>
          <Text style={styles.buttonText}>
            🔍 Processar {photos.length} fotos
          </Text>
        </TouchableOpacity>
      )}

      <TouchableOpacity 
        style={styles.secondaryButton}
        onPress={() => navigation.navigate('Gains')}
      >
        <Text style={styles.buttonText}>💰 Controle de Ganhos</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f8f9fa',
    justifyContent: 'center'
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 40,
    color: '#333'
  },
  button: {
    backgroundColor: '#007bff',
    padding: 15,
    borderRadius: 25,
    marginBottom: 15,
    elevation: 3
  },
  processButton: {
    backgroundColor: '#28a745',
    padding: 15,
    borderRadius: 25,
    marginBottom: 15,
    elevation: 3
  },
  secondaryButton: {
    backgroundColor: '#6c757d',
    padding: 15,
    borderRadius: 25,
    marginBottom: 15,
    elevation: 3
  },
  buttonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    textAlign: 'center'
  }
});

export default HomeScreen;
```

### NavigationScreen.js
```jsx
import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, Linking, StyleSheet, Alert } from 'react-native';
import Geolocation from 'react-native-geolocation-service';
import PushNotification from 'react-native-push-notification';

const NavigationScreen = ({ route }) => {
  const { deliveries } = route.params;
  const [currentIndex, setCurrentIndex] = useState(0);
  const [completedDeliveries, setCompletedDeliveries] = useState([]);
  const [userLocation, setUserLocation] = useState(null);

  useEffect(() => {
    getCurrentLocation();
    scheduleNotifications();
  }, []);

  const getCurrentLocation = () => {
    Geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude
        });
      },
      (error) => console.error('Location error:', error),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 }
    );
  };

  const scheduleNotifications = () => {
    deliveries.forEach((delivery, index) => {
      if (index > currentIndex) {
        PushNotification.localNotificationSchedule({
          title: "Próxima Entrega",
          message: `${delivery.address}`,
          date: new Date(Date.now() + (index - currentIndex) * 10 * 60 * 1000), // 10 min cada
          id: index
        });
      }
    });
  };

  const openInMaps = (address) => {
    const encodedAddress = encodeURIComponent(address);
    const mapsUrl = `https://www.google.com/maps/search/${encodedAddress}`;
    Linking.openURL(mapsUrl);
  };

  const openInWaze = (address) => {
    const encodedAddress = encodeURIComponent(address);
    const wazeUrl = `https://waze.com/ul?q=${encodedAddress}`;
    Linking.openURL(wazeUrl);
  };

  const markAsDelivered = () => {
    const newCompleted = [...completedDeliveries, currentIndex];
    setCompletedDeliveries(newCompleted);
    
    if (currentIndex < deliveries.length - 1) {
      setCurrentIndex(currentIndex + 1);
    } else {
      Alert.alert(
        "🎉 Parabéns!",
        `Todas as ${deliveries.length} entregas foram concluídas!`,
        [{ text: "OK", onPress: () => navigation.goBack() }]
      );
    }
  };

  const currentDelivery = deliveries[currentIndex];
  const progress = `${currentIndex + 1}/${deliveries.length}`;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.progress}>{progress}</Text>
        <Text style={styles.status}>
          {completedDeliveries.length} concluídas
        </Text>
      </View>

      <View style={styles.deliveryCard}>
        <Text style={styles.deliveryNumber}>
          Entrega {currentIndex + 1}
        </Text>
        <Text style={styles.address}>{currentDelivery?.address}</Text>
        
        <View style={styles.actionButtons}>
          <TouchableOpacity 
            style={[styles.actionButton, styles.mapsButton]}
            onPress={() => openInMaps(currentDelivery.address)}
          >
            <Text style={styles.actionButtonText}>🗺️ Maps</Text>
          </TouchableOpacity>

          <TouchableOpacity 
            style={[styles.actionButton, styles.wazeButton]}
            onPress={() => openInWaze(currentDelivery.address)}
          >
            <Text style={styles.actionButtonText}>🚗 Waze</Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity 
          style={styles.deliveredButton}
          onPress={markAsDelivered}
        >
          <Text style={styles.deliveredButtonText}>✅ Entregue</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.remainingList}>
        <Text style={styles.remainingTitle}>Próximas Entregas:</Text>
        {deliveries.slice(currentIndex + 1).map((delivery, index) => (
          <Text key={index} style={styles.remainingItem}>
            {currentIndex + index + 2}. {delivery.address}
          </Text>
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
    padding: 20
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
    padding: 15,
    backgroundColor: '#007bff',
    borderRadius: 10
  },
  progress: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold'
  },
  status: {
    color: 'white',
    fontSize: 16
  },
  deliveryCard: {
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 15,
    marginBottom: 20,
    elevation: 5
  },
  deliveryNumber: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#007bff',
    marginBottom: 10
  },
  address: {
    fontSize: 16,
    color: '#333',
    marginBottom: 20,
    lineHeight: 22
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 15
  },
  actionButton: {
    flex: 1,
    padding: 12,
    borderRadius: 8,
    alignItems: 'center'
  },
  mapsButton: {
    backgroundColor: '#4285f4'
  },
  wazeButton: {
    backgroundColor: '#00d4ff'
  },
  actionButtonText: {
    color: 'white',
    fontWeight: 'bold'
  },
  deliveredButton: {
    backgroundColor: '#28a745',
    padding: 15,
    borderRadius: 25,
    alignItems: 'center'
  },
  deliveredButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold'
  },
  remainingList: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    elevation: 3
  },
  remainingTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#333'
  },
  remainingItem: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5
  }
});

export default NavigationScreen;
```

## ⚡ Comparação: Bot vs Apps

| Recurso | Bot Telegram | PWA | React Native | Capacitor |
|---------|-------------|-----|--------------|-----------|
| **Desenvolvimento** | ✅ Rápido | ✅ Rápido | 🟡 Médio | ✅ Rápido |
| **Performance** | 🟡 Limitado | ✅ Boa | ✅ Excelente | ✅ Boa |
| **Offline** | ❌ Não | ✅ Sim | ✅ Sim | ✅ Sim |
| **Recursos Nativos** | ❌ Limitado | 🟡 Alguns | ✅ Todos | ✅ Muitos |
| **App Stores** | ❌ Não | 🟡 Parcial | ✅ Sim | ✅ Sim |
| **Câmera** | 🟡 Básica | ✅ Avançada | ✅ Nativa | ✅ Nativa |
| **GPS** | ❌ Não | ✅ Sim | ✅ Nativo | ✅ Nativo |
| **Notificações** | 🟡 Telegram | ✅ Web | ✅ Nativas | ✅ Nativas |
| **Custos** | ✅ Gratuito | ✅ Baixo | 🟡 Médio | ✅ Baixo |

## 🎯 Recomendação

Para transformar seu bot em um app pessoal, eu recomendaria esta ordem:

### 1. **Começar com PWA** (mais rápido)
- Use o código Flask que criei
- Instale como app no celular
- Teste todas as funcionalidades
- Custa quase nada para começar

### 2. **Evoluir para Capacitor** (se quiser app stores)
- Aproveita o código PWA
- Adiciona recursos nativos
- Publica nas lojas de app
- Boa relação custo/benefício

### 3. **React Native** (se precisar performance máxima)
- App 100% nativo
- Performance superior
- Mais recursos avançados
- Requer mais tempo/investimento

## 🚀 Próximos Passos

Quer que eu ajude a implementar qual opção? Posso:

1. **Completar o PWA**: Adicionar OCR real, otimização de rotas, etc.
2. **Configurar Capacitor**: Transformar em app instalável
3. **Criar React Native**: App nativo completo
4. **Migrar dados**: Do bot atual para o app

O que prefere começar?
