---
title: "dados-relatorios"
category: "dados"
tags:
  - "Relatórios"
  - "Como gerar relatórios"
  - "Relatório Geral"
  - "Relatório de Ordens de Serviço"
  - "Relatório de Alarmes"
---
# Relatórios

<script setup>
import { withBase } from 'vitepress'
</script>

## Como gerar relatórios

Vá até a tela de relatórios, clique em **CRIAR NOVO RELATÓRIO** e selecione o tipo de relatório desejado:

![Indicadores Relatório Geral](/assets/articles/relatorios/Relatorios1n.gif)

Após selecionar o tipo de relatório, selecione os filtros que deseja aplicar e preencha o nome e o tipo de documento (PDF ou CSV). Há também a opção de **personalizar relatório**, que permite selecionar as informações que serão exibidas no relatório. Por fim, clique em **GERAR RELATÓRIO**; o documento entrará na fila e, quando estiver pronto para download, ficará exibido na tela inicial de relatórios e também será enviada por email.

![Indicadores Relatório Geral](/assets/articles/relatorios/Relatorios2n.gif)

Para os **Relatório de Ordem de serviço** é possível escolher se o filtro de data será aplicado na data de abertura ou na data de finalização.

![Indicadores Relatório Geral](/assets/articles/relatorios/Relatorios3n.gif)


## Relatório Geral

O **Relatório Geral** é mensal e unifica a análise de desempenho, disponibilidade e performance em um único documento. Nele, são apresentados os dados comparativos entre a geração real e a projetada pela simulação PVsyst para os períodos mensal e diário, além de um resumo geral dos alarmes apresentados por cada tipo de equipamento.

![Indicadores Relatório Geral](/assets/articles/relatorios/Relatorios3.gif)

## Relatório de Ordens de Serviço

O **Relatório de Ordens de Serviço** unifica a análise das ordens de serviço do sistema, apresentando de forma consolidada as principais informações de cada **OS**. O relatório exibe as datas de referência (abertura e finalização), a descrição de abertura, o tempo de atraso, os documentos anexados (fotos, vídeos, PDFs, entre outros), os equipamentos vinculados, os alarmes associados, os comentários registrados e a descrição de finalização da ordem.

![Indicadores Relatório Geral](/assets/articles/relatorios/Relatorios4.gif)

## Relatório de Alarmes

O **Relatório de Alarmes** consolida a análise dos alarmes registrados no sistema, permitindo o acompanhamento detalhado dos eventos operacionais e de falha. O relatório apresenta, para cada alarme, as datas e horários de início e fim, a duração do evento, o nível de severidade, o status (ativo, normalizado ou reconhecido), a descrição do alarme, o equipamento associado e a usina de origem. Também são exibidas informações adicionais como comentários, histórico de ocorrências e indicadores que auxiliam na identificação de padrões recorrentes e no diagnóstico de falhas, apoiando a tomada de decisão e a manutenção preventiva.

![Indicadores Relatório Geral](/assets/articles/relatorios/Relatorios5.gif)
