---
title: "dashboards-operacao"
category: "dashboards"
tags:
  - "Dashboard de Operação"
  - "Mapa"
  - "Tabela de Alarmes"
  - "Resumo Geral"
---
# Dashboard de Operação

<script setup>
import { withBase } from 'vitepress'
</script>

## Mapa

No mapa do **Dashboard de Operação** é possível visualizar todas as usinas atribuídas ao seu usuário. Ao clicar no ícone de uma usina, é possível monitorá-la individualmente, sendo transferido para a página Dashboard Usina.

![Mapa - Dashboard Operação](/assets/articles/operacao/DashboardOperacao1.png)

É possível filtrar a exibição das usinas por Tipo de Instalação, O&M, Localização ou selecioná-las individualmente.

### Status da Usina

A coloração das usinas no mapa varia de acordo com os alarmes ativos no momento, seguindo o padrão abaixo:

- **Normal:**
Sistema em operação normal, sem alarmes ativos.
- **Atenção:**
Presença de pelo menos 1 alarme de atenção ou sem comunicação em SKID ou CMP
Entre 15% e 50% da potência dos inversores está associada a equipamentos com alarmes críticos ou de atenção.
De 15% a 50% dos trackers e strings apresentam alarmes de nível crítico, atenção ou estão sem comunicação
- **Sem Comunicação:**
Perda de comunicação com o data logger
Perda de comunicação com todos inversores
- **Crítico:**
Mais de 50% da potência total dos inversores está associada a equipamentos com alarmes críticos, de atenção ou fora de comunicação.
Um ou mais alarmes de nível crítico em CMP
Um ou mais alarmes de nível crítico em SKID
Mais de 50% dos trackers e strings apresentam alarmes de nível crítico, atenção ou estão sem comunicação.

<!-- ## Tabela de O.S.

Ao lado do mapa fica a tabela de Ordens de Serviço, onde ficam expostas as OSs associadas ao seu usuário. Cada OS possui 6 atributos:

- **ID:** Identificador da OS no sistema.
- **Flags:** Indicam se um OS possui arquivos associados, se ela foi criada a partir de um alarme e/ou se está em atraso.
- **Status:** Indica o estágio de conclusão da OS (Aberto, Finalizado ou Em andamento).
- **Categoria:** Indica a categoria da OS.
- **Usina:** Indica a usina à qual a OS está associada.
- **Data da última interação:** Data e hora da última interação com a OS.

É possível visualizar a OS ao clicar no botão da última coluna da tabela.

![Botão visualizar ordem de serviço](/assets/img/placeholder.jpg) -->

## Tabela de Alarmes

Sobreposta ao Mapa, fica a tabela de alarmes ativos. Nela, ficam exibidos os alarmes ativos por tipo de equipamento, ordenados de forma descrescente pela severidade.

![Tabela de Alarmes - Dashboard Operação](/assets/articles/operacao/DashboardOperacao2.png)

Para cada alarme, é possível reconhecê-lo, clicando no ícone de olho, ou abrir uma OS, clicando no ícone de ticket.

## Resumo Geral

Logo abaixo do mapa e da tabela de OS é exibido o resumo geral das usinas, mostrando o status dos equipamentos por tipo. A lista é ordenada, por padrão, em ordem decrescente de severidade, priorizando estados ‘Crítico’ em relação a ‘OK’.

![Resumo Geral - Dashboard Operação](/assets/articles/operacao/DashboardOperacao3.png)

<!-- ## Alarmes Ativos

Abaixo do Resumo Geral, fica a lista dos alarmes ativos, separados por tipo de equipamento. No canto superior direito da lista de alarmes ativos, é possível gerar um relatório de alarmes.

![Botão relatório de alarmes](/assets/img/placeholder.jpg)

Além disso, na tabela de alarmes ativos é possível criar uma OS a partir de um alarme, ou visualizar o equipamento que apresenta o alarme.

![Botão criar OS](/assets/img/placeholder.jpg) -->
