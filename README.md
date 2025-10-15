# 🕒 Pi Clock – Relógio Inteligente com Raspberry Pi

---

## 🧩 Primeira Versão (T2)

O **Pi Clock** é um relógio inteligente desenvolvido em **Python**, pensado para rodar em uma **Raspberry Pi 3** com **display touchscreen de 7 polegadas**.  

Ele exibe **hora em tempo real**, **data atual**, **dia da semana**, além da **previsão do tempo local** obtida via API. Também permite criar, editar e excluir **alarmes programados**, que podem ser adiados com um botão de **soneca**.  

---

### 🔧 Componentes do Sistema

- 🧠 **Raspberry Pi 3** (plataforma de desenvolvimento e processamento)  
- 🖥️ **Display touchscreen de 7”** (interface gráfica)  
- 🔊 **Buzzer** (alerta sonoro dos alarmes)  
- 📡 **Conexão Wi-Fi** (sincronização de hora e obtenção da previsão do tempo via API)  
- 🔋 **Fonte de alimentação / bateria (opcional)** (funcionamento contínuo sem energia externa)  
- ⏰ **Módulo RTC (opcional)** (manter horário mesmo sem internet)  

---

### 🕹️ Funcionalidades

- Exibir **hora em tempo real**  
- Mostrar **data atual** e **dia da semana**  
- Obter e exibir **temperatura atual**, **mínima** e **máxima do dia** via API OpenWeatherMap  
- Criar, editar e excluir **alarmes programados**  
- Exibir o **próximo alarme** na tela principal  
- Botão de **soneca** (adiar o alarme em 5 minutos)  
- Emissão de alerta sonoro por **buzzer** ao disparar o alarme  
- Interface gráfica intuitiva com **suporte a touchscreen**  

---

### 🎯 Objetivo

Este projeto foi desenvolvido como parte da disciplina **EEN251 - Microcontroladores e Sistemas Embarcados**, com o objetivo de integrar conceitos de **hardware** (Raspberry Pi, display, buzzer) e **software** (Python, Tkinter, API de clima), resultando em um sistema embarcado funcional.  

---

### 👨‍💻 Integrantes

- Sérgio Guidi Trovo — 22.01128-5  
- Leonardo Galdi Fiorese — 22.00952-3  
- Rodrigo Monasterios Morales Reis — 22.01432-2  
- Enrico Mota Santarelli — 22.00370-3  

---

# 🚀 Segunda Versão (T3)

Na segunda versão do **Pi Clock**, o projeto foi aprimorado com **integração total à plataforma IoT Ubidots**, permitindo **monitoramento e controle remoto do relógio e dos alarmes** diretamente pela nuvem.  

Essa atualização transforma o Pi Clock em um **sistema IoT completo**, com comunicação bidirecional entre a Raspberry Pi e o Ubidots, ampliando suas possibilidades de uso e automação.

---

## 🌐 Integração com o Ubidots

### 📡 Comunicação bidirecional

O sistema agora envia e recebe dados do **Ubidots Industrial API**.  
- **Envio de dados:** temperatura, hora, data, alarmes tocados, eventos de soneca, etc.  
- **Recebimento de comandos:** tocar, parar ou criar alarmes diretamente do dashboard.  

A comunicação ocorre via **requisições HTTP (REST API)** com autenticação por token.

---

### ⚙️ Funcionalidades adicionadas

#### 🔹 Envio de dados para o Ubidots
- Atualização periódica de **temperatura atual, mínima e máxima**, descrição do clima e timestamp.  
- Envio de **eventos de alarme tocado** e **alarme adiado (soneca)**.  
- Registro de **data e hora exatas** em que o alarme foi acionado.  

#### 🔹 Controle remoto do alarme
- A variável `remote_alarm_trigger` permite **ligar e desligar o alarme** remotamente:  
  - Valor `1` → tocar o alarme.  
  - Valor `0` → parar o alarme.  
- O comando pode ser enviado diretamente do **dashboard do Ubidots** através de um switch.

#### 🔹 Criação remota de alarmes
- É possível **criar alarmes remotamente** através do dashboard, utilizando variáveis como:  
  - `new_alarm_hour`  
  - `new_alarm_minute`  
  - `new_alarm_days`  
  - `create_alarm_trigger`  
- Quando o Ubidots envia `create_alarm_trigger = 1`, o PiClock cria automaticamente um novo alarme local na Raspberry Pi.

#### 🔹 Comunicação assíncrona (sem travamentos)
- As chamadas à API do Ubidots foram implementadas com **threads**, evitando bloqueios no Tkinter.  
- Assim, a interface permanece fluida mesmo durante o envio ou recebimento de dados.  

---

## 📊 Painel no Ubidots

O dashboard do Ubidots foi configurado com:
- **Switches** para tocar e parar o alarme (`remote_alarm_trigger`).  
- **Campos de entrada** para definir hora e minuto de novos alarmes (`new_alarm_hour` e `new_alarm_minute`).  
- **Botão “Criar Alarme”** que envia `create_alarm_trigger = 1`.  
- **Gráficos** exibindo histórico de temperaturas e eventos de alarme.  

Isso permite **controle remoto completo** do Pi Clock diretamente pela web.

---

## 🧠 Arquitetura do Sistema IoT

```text
        ┌──────────────────────────────┐
        │         Dashboard             │
        │   (Ubidots Cloud Platform)    │
        └──────────────┬───────────────┘
                       │ (REST API HTTPS)
                       ▼
        ┌──────────────────────────────┐
        │     Raspberry Pi 3 + PiClock  │
        │  Python + Tkinter + Threads   │
        └──────────────┬───────────────┘
                       │
                       ▼
              ⏰ Alarmes Locais
```

## 🧩 Tecnologias Utilizadas

- **Python 3**
- **Tkinter** (interface gráfica)
- **Threading** (execução assíncrona)
- **Requests** (requisições HTTP)
- **OpenWeatherMap API** (dados meteorológicos)
- **Ubidots Industrial API** (plataforma IoT)
- **JSON e dotenv** (armazenamento e configuração)

---

## 🛠️ Estrutura de Arquivos

```text
PiClock/
│
├── piclock.py              # Código principal da aplicação
├── alarms.json             # Armazenamento local dos alarmes
├── audio.py                # Gerenciamento de reprodução de som
├── .env                    # Token do Ubidots e chave da API do clima
└── README.md               # Documentação do projeto
```

## 🚀 Possibilidades Futuras

- Implementar **histórico de alarmes** diretamente no Ubidots.  
- Adicionar **controle por voz ou via assistente virtual**.  
- Integrar **sensores adicionais** (luminosidade, presença, etc.).  
- Publicar uma **versão mobile ou web** para controle remoto completo.

---

## 🏁 Conclusão

A segunda versão do **Pi Clock** amplia consideravelmente o escopo do projeto original, transformando-o em um **sistema embarcado IoT completo**, capaz de:  
- coletar e enviar dados meteorológicos,  
- ser controlado remotamente,  
- e criar alarmes pela nuvem.  

Essa integração com o **Ubidots** demonstra, de forma prática, o potencial da **Internet das Coisas (IoT)** aplicada a dispositivos embarcados.
