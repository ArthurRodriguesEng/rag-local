---
title: "dashboards-performance"
category: "dashboards"
tags:
  - "Dashboard de Performance"
  - "Tabela de Performance"
  - "Gráficos de Calor"
  - "Análise de Performance Detalhada"
---
# Dashboard de Performance

<script setup>
import { withBase } from 'vitepress'
</script>

## Tabela de Performance

Na Tabela de Performance, são apresentados os dados para análise de performance da usina. No seletor de data, acima da tabela, é possível alternar entre a visualização de dados diários e mensais.
 
![Tabela Dashboard Performance](/assets/articles/performance/DashboardPerformance1n.gif)

Na tabela, são apresentados os seguintes dados da UFV:

- **Potência pico (kW)**
- **Potência nominal (kW)**
- **Geração:** Acumulados de Geração (Verde: real, Azul: estimado, Vermelho: projetado PVsyst, Branco: injetado).
- **Irradiação:** Laranja (real) e Vermelho (projetada PVsyst).
- **Geração / Estimado (%):** Relação entre a Geração Real e a Estimada.
- **PR (Performance Ratio):** Razão entre a geração esperada, dada a irradiação, e a real.
- **Disponibilidade:** Razão entre o tempo útil dos inversores sobre o tempo total de geração.
- **PR / Meta (%):** Relação entre o PR Real e o projetado (PVsyst).

## Gráficos de Calor

Abaixo da Tabela de Performance, os dados da tabela são exibidos no formato mapa de calor, apresentando colorações esverdeadas para valores mais próximos a 100% e avermelhadas para valores próximos a 0%.

![Tabela Dashboard Performance](/assets/articles/performance/DashboardPerformance2.gif)

## Análise de Performance Detalhada

Ao clicar em um dia dos mapas de calor, abre-se uma nova subtela com a **Análise de Performance** diária da usina.

![Análise de Performance diária](/assets/articles/performance/DashboardPerformance3.gif)

Nesta tela, temos a análise de potência ativa por inversor, análise de perdas, yields e disponibilidade dos inversores, além de posição e target de TCUs e histórico de alarmes.

Clicando no botão no canto superior direito da tela, podemos exportá-la no formato de relatório em PDF.

![Export da Tela Análise de Performance](/assets/articles/performance/DashboardPerformance4.png)
