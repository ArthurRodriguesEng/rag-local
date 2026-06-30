---
title: "cmms-ordens-servico"
category: "cmms"
tags:
  - "Ordens de Serviço"
  - "Calendário"
  - "Criando OS's"
  - "Categorias e Subcategorias"
---
# Ordens de Serviço

<script setup>
import { withBase } from 'vitepress'
</script>

![Alternar visualização](/assets/articles/ordens_de_servico/OrdensServico1_n.gif)

Na tela **Ordens de Serviço**, ficam listadas as ordens de serviço de acordo com os filtros selecionados:

- **Tipo de Manutenção**
- **Atribuição** (Criadas pelo usuário ou atribuídas a ele)
- **Status** (Criado, Aberto, Em andamento, Finalizado)
- **Estado**
- **Usina**
- **O&M**
- **Usuários Atribuídos**
- **Criado por**
- **Categoria e Subcategoria**
- **Sistema**
- **Categoria**
- **Subcategoria**
- **ID**

Por padrão, o filtro de data é aplicado na data de criação da ordem de serviço, mas é possível selecionar para ser aplicado na data de finalização.

## Calendário

No canto superior esquerdo da tela, é possível alternar a visualização entre os formatos de **tabela** e **calendário**.

![Ordens de Serviço](/assets/articles/ordens_de_servico/OrdensServico1.png)

Na visualização de calendário, as OSs ficam dispostas em ordem cronológica. É possível alternar entre os períodos mensal, semanal e diário.

> É possível clicar e arrastar uma ordem de serviço para outro dia no calendário, remarcando-a para o dia selecionado.

![Alternar visualização](/assets/articles/ordens_de_servico/OrdensServico1.gif)

## Criando OS's

Na criação de ordens de serviço, é possível definir todas as propriedades apresentadas. Além disso, também é possível limitar o acesso desta funcionalidade apenas aos usuários desejados. Assista ao vídeo abaixo e aprenda como utilizar este recurso:

<iframe width="100%" height="400" src="https://www.youtube.com/embed/9V2fUbhgaU8?rel=0&modestbranding=1&showinfo=0" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>

Para criar uma OS, clique no botão "Criar Nova Ordem de Serviço" e preencha os campos obrigatórios (Título, Descrição, Categoria, Subcategoria, Tipo de Manutenção, Usina).

## Categorias e Subcategorias

As categorias e subcategorias são fundamentais para a estruturação e gestão eficiente das ordens de serviço. Pensando nisso, o sistema TECSCI oferece uma relação padrão pronta para uso, mas também garante total flexibilidade para que o usuário crie novas classificações, adaptando a plataforma à realidade da sua empresa. Assista ao vídeo abaixo e aprenda como utilizar este recurso:

<iframe width="100%" height="400" src="https://www.youtube.com/embed/UQRnctEIjGU?si=7MfADR6-94cPxPba&rel=0&modestbranding=1&showinfo=0" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>

> **Importante:** Ao apagar uma Categoria ou Subcategoria, as OSs que a utilizam **não** serão apagadas.
