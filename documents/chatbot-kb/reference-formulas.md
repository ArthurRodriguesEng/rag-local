---
title: "reference-formulas"
category: "reference"
tags:
  - "Fórmulas Utilizadas"
  - "Performance Ratio"
  - "Potência Esperada Instantânea"
  - "Energia Esperada no Período"
  - "Fator Capacidade"
  - "Yields"
  - "Disponibilidade"
---
# Fórmulas Utilizadas

## Performance Ratio

$$
PR = \frac{E_{total}}{Pot_{nom} \cdot \frac{I_{POA}}{I_{STC}}}
$$

Onde:

*   $E_{total}$ = Energia total medida no período [kWh]
*   $Pot_{nom}$ = Potência nominal da usina [kW]
    *   A potência nominal é calculada como: $Pot_{nom} = A_{modulos} \cdot \eta_{modulo}$
    *   $A_{modulos}$ = Área de todos os módulos da usina (N° de módulos x Área do módulo) [m²]
    *   $\eta_{modulo}$ = Eficiência padrão do módulo sob condições STC [\%]
*   $I_{POA}$ = Irradiação no Plano dos Módulos total do período [kWh/m²]
*   $I_{STC}$ = Irradiação em condições normais de ensaio = 1 [kW/m²]

## Potência Esperada Instantânea

$$
P_{esp} = \min\left(P_{calc}, P_{inversor}\right)
$$

$$
P_{calc} = \eta_{cabos} \cdot \eta_{T} \cdot \beta_{bifacial} \cdot \frac{I_{POA} \cdot A_{modulos} \cdot \eta_{modulo}}{1000}
$$

$$
\eta_{cabos} = 1 - L_{cabos}
$$

$$
\eta_{T} = (1 - (T_{modulo} - T_{STC}) \cdot C_T)
$$

$$
\beta_{bifacial} = (1 + G_{bifacial})
$$

Onde:

*   $P_{esp}$ = Potência esperada [kW]
*   $P_{calc}$ = Potência DC calculada após aplicação das perdas [kW]
*   $P_{inversor}$ = Potência máxima do inversor [kW]
<!-- *   $E_{esp}$ = Energia esperada no período [kWh] -->
*   $\eta_{cabos}$ = Coeficiente de perda por cabos [\%]
*   $\eta_{T}$ = Coeficiente de perda por temperatura [\%]
*   $\beta_{bifacial}$ = Coeficiente de bifacialidade [\%]
*   $I_{POA}$ = Irradiância no Plano dos Módulos total [W/m²]
*   $A_{modulos}$ = Área de todos os módulos da usina (N° de módulos x Área do módulo) [m²]
*   $\eta_{modulo}$ = Eficiência dos módulos
*   $L_{cabos}$ = Perda por cabeamento = 2.5% = 0.025 
*   $T_{modulo}$ = Temperatura do módulo no período [°C]
*   $T_{STC}$ =  Temperatura do módulo em condições normais de ensaio = 25 [°C]
*   $C_T$ = Coeficiente de perda de eficiência pelo gradiente de Temperatura (datasheet) [-\%/°C]
*   $G_{bifacial}$ = Ganho de potência da parte traseira (datasheet)

:::tip NOTA
Interrupções na leitura de Irradiação podem causar a indisponibilidade no cálculo da Energia Esperada no dia da ocorrência.
:::

## Energia Esperada no Período

A energia é calculada através da integral da potência instantânea ao longo do período analisado. Como a potência esperada é discreta no tempo, temos:

$$
E_{esp} = \sum_{i=1}^{n} \left( \frac{P_{esp\_i} + P_{esp\_i-1}}{2} \cdot \Delta t_i \right)
$$

$$
\Delta t = t_{i} - t_{i-1}
$$

**Onde:**

*   $E_{esp}$ = Energia esperada acumulada no período [kWh]
*   $P_{esp\_i}$ = Potência esperada instantânea calculada na amostra $i$ [kW]
*   $P_{esp\_i-1}$ = Potência esperada instantânea calculada na amostra anterior [kW]
*   $\Delta t_i$ = Intervalo de tempo entre a leitura atual e a anterior [h]
*   $n$ = Número total de amostras válidas no período analisado
*   $t_{i}, t_{i-1}$ = Tempo no período atual e no período anterior [h]


## Fator Capacidade

$$
FC = \frac{\frac{E_{total}}{Pot_{nom}}}{24 h \cdot N_{dias}}
$$

Onde:

*   $E_{total}$ = Energia total medida no período [kWh]
*   $Pot_{nom}$ = Potência nominal [kW]
*   $N_{dias}$ = Número de dias do período analisado [dias]

## Yields

### Yield de referência

$$
Y_{ref} = \frac{I_{POA}}{I_{STC}}
$$

Onde:

*   $I_{POA}$ = Irradiação no Plano dos Módulos total do período [kWh/m²]
*   $I_{STC}$ = Irradiância em condições normais de ensaio = 1 [kW/m²]

### Yield específico

$$
Y_{esp} = \frac{E_{total}}{Pot_{pico}}
$$

Onde:

*   $E_{total}$ = Energia total medida no período [kWh]
*   $Pot_{pico}$= Potência pico da usina [kWp]

## Disponibilidade

$$
Disp = \frac{T_{Disp}}{T_{Util}}
$$

$$
T_{Disp} = T_{Util} - T_{Indisp}
$$

Onde:

*   $Disp$ = Disponibilidade do equipamento [\%]
*   $T_{Disp}$ = Tempo de disponibilidade [h]
*   $T_{Indisp}$ = Tempo de indisponibilidade, considerado somatório dos tempos de alarmes críticos em horário útil de geração [h]
*   $T_{Util}$= Tempo útil de geração, de 6:00 às 18:00 [h]
