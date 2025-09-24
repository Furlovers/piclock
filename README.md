# Pi Clock

O **Pi Clock** é um relógio inteligente desenvolvido em **Python**, pensado para rodar em uma **Raspberry Pi 3** com **display touchscreen de 7 polegadas**.  

Ele exibe **hora em tempo real**, **data atual**, **dia da semana**, além da **previsão do tempo local** obtida via API. Também permite criar, editar e excluir **alarmes programados**, que podem ser adiados com um botão de **soneca**.  

---

## 🔧 Componentes do Sistema

- 🧠 **Raspberry Pi 3** (plataforma de desenvolvimento e processamento)  
- 🖥️ **Display touchscreen de 7”** (interface gráfica)  
- 🔊 **Buzzer** (alerta sonoro dos alarmes)  
- 📡 **Conexão Wi-Fi** (sincronização de hora e obtenção da previsão do tempo via API)  
- 🔋 **Fonte de alimentação / bateria (opcional)** (funcionamento contínuo sem energia externa)  
- ⏰ **Módulo RTC (opcional)** (manter horário mesmo sem internet)  

---

## 🕹️ Funcionalidades

- Exibir **hora em tempo real**  
- Mostrar **data atual** e **dia da semana**  
- Obter e exibir **temperatura atual**, **mínima** e **máxima do dia** via API OpenWeatherMap  
- Criar, editar e excluir **alarmes programados**  
- Exibir o **próximo alarme** na tela principal  
- Botão de **soneca** (adiar o alarme em 5 minutos)  
- Emissão de alerta sonoro por **buzzer** ao disparar o alarme  
- Interface gráfica intuitiva com **suporte a touchscreen**  

---

## 🎯 Objetivo

Este projeto foi desenvolvido como parte da disciplina **EEN251 - Microcontroladores e Sistemas Embarcados**, com o objetivo de integrar conceitos de **hardware** (Raspberry Pi, display, buzzer) e **software** (Python, Tkinter, API de clima), resultando em um sistema embarcado funcional.  

---

## 👨‍💻 Integrantes

- Sérgio Guidi Trovo — 22.01128-5  
- Leonardo Galdi Fiorese — 22.00952-3  
- Rodrigo Monasterios Morales Reis — 22.01432-2  
- Enrico Mota Santarelli — 22.00370-3
