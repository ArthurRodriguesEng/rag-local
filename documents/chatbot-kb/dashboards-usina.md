---
title: "dashboards-usina"
category: "dashboards"
tags:
  - "Dashboard Usina"
  - "Mapa"
  - "Análise Energética"
  - "Análise de Inversores"
  - "Análise de Perdas"
---
# Dashboard Usina

<script setup>
import { withBase } from 'vitepress'
</script>

## Mapa

![Visualização dinâmica e em diagrama](/assets/articles/usina/DashboardUsina1.png)

No mapa do **Dashboard Usina** é possível visualizar individualmente todos os equipamentos da usina. A cor dos equipamentos no mapa varia de acordo com seu status:

<div style="display: flex; flex-direction: column; gap: 8px; font-size: 115%;">
  <div style="display: flex; align-items: center;">
    <span style="
      color:#db0606;
      width: 28px;
      height: 1em;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 135%;
      line-height: 1;
      transform: translateY(-0.12em);
    ">■</span>
    <span style="margin-left: 8px;"><strong>Crítico</strong></span>
  </div>

  <div style="display: flex; align-items: center;">
    <span style="
      color:#e0d013;
      width: 28px;
      height: 1em;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 130%;
      line-height: 1;
    ">▲</span>
    <span style="margin-left: 8px;"><strong>Atenção</strong></span>
  </div>

  <div style="display: flex; align-items: center;">
    <span style="
      color:#ff9850;
      width: 28px;
      height: 1em;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 130%;
      line-height: 1;
    ">▼</span>
    <span style="margin-left: 8px;"><strong>Sem comunicação</strong></span>
  </div>

  <div style="display: flex; align-items: center;">
    <span style="
      color:#00e74f;
      width: 28px;
      height: 1em;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 130%;
      line-height: 1;
    ">◆</span>
    <span style="margin-left: 8px;"><strong>Normal</strong></span>
  </div>
</div>


No canto superior direito do mapa, você pode alternar entre duas visualizações:

- **Visualização dinâmica:** Exibe os equipamentos sobre imagens de satélite.
- **Visualização em diagrama:** Exibe os equipamentos sobre um fundo neutro.


## Análise Energética

Logo abaixo do mapa, encontram-se os gráficos de Análise Energética, nos quais é possível acompanhar a geração e a irradiação reais e projetadas da usina, com visualização diária, mensal ou anual. A exibição dos dados projetados depende do cadastro prévio no PVsyst.

![Visualização dinâmica e em diagrama](/assets/articles/usina/DashboardUsina2n.png)

Para alterar o período de análise, selecione as datas pelo seletor localizado acima dos gráficos:

![Visualização dinâmica e em diagrama](/assets/articles/usina/DashboardUsina3n.gif)


## Análise de Inversores

Abaixo dos gráficos de análise energética, temos os gráficos de análise de inversores, indicando os dados de geração e yield por inversor da UFV. Para ambos os dados, há duas versões do gráfico: gráfico de calor e de barra.

![Visualização dinâmica e em diagrama](/assets/articles/usina/DashboardUsina4.gif)


## Análise de Perdas

Abaixo dos gráficos de análise de inversor, temos os gráficos de **Potência Ativa por Inversor** e **Análise de Perdas**, a partir dos quais é possível avaliar, de forma detalhada, o desempenho energético da usina e identificar as principais fontes de limitação da geração.

![Análise de Perdas](/assets/articles/usina/DashboardUsina5.png)

A **Análise de Perdas** permite uma visão aprofundada da geração elétrica de uma UFV, comparando a potência efetivamente entregue com os valores teóricos estimados a partir das condições de irradiância e características do sistema. No gráfico, são listadas as seguintes variáveis principais:

- **Potência real:** Exibe a potência ativa real gerada pela usina e medida no ponto de acoplamento.
- **Potência estimada:** Exibe a potência estimada da usina com base na irradiância incidente e nos parâmetros do sistema, já considerando as perdas.
- **Potência estimada DC:** Exibe a potência estimada no lado DC, representando o cenário ideal sem perdas associadas a clipping, cabeamento, temperatura e demais limitações.

- **Ganho bifacial:** Quando aplicável, representa o acréscimo de geração proveniente da captação de irradiância pelo lado posterior dos módulos bifaciais.
- **Perda por cabeamento:** Indica as perdas elétricas associadas à resistência dos cabos no sistema.
- **Perda por clipping:** Representa a limitação de potência causada pela saturação dos inversores quando a potência DC disponível excede sua capacidade nominal.
- **Perda por temperatura:** Demonstra a redução de desempenho dos módulos devido ao aumento da temperatura de operação.
- **Irradiância POA (Plane of Array):** Exibe a irradiância incidente no plano dos módulos, utilizada como base para o cálculo das potências estimadas.

Com essas informações, é possível identificar gargalos operacionais, avaliar o impacto de cada tipo de perda e apoiar decisões técnicas para otimização do desempenho da usina.
