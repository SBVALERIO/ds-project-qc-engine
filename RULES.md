# Regras do DS Project QC

Lista do que o motor verifica hoje, pra você conferir. Adiciona novas ideias
na seção **Regras propostas** no final — quando quiser, me manda esse arquivo
(ou só a parte nova) que eu implemento e volto aqui pra marcar como ativa.

## Regras ativas (sempre rodam)

| # | Regra | O que verifica |
|---|-------|-----------------|
| 1 | Typos sistêmicos | Erros de digitação conhecidos (ex.: "LENGHT" em vez de "LENGTH") que se repetem pelo pacote inteiro, sinalizados como uma correção só ("corrigir em todo lugar"), não um achado por prancha. |
| 2 | Código duplicado em schedule/legenda | Um mesmo código (ex.: "D2", "CE04") aparecendo em mais de uma linha *distinta* dentro da mesma tabela — o que deixa ambíguo qual linha um callout na planta está referenciando. |
| 3 | Quantidade placeholder | Quantidade do tipo "XX SQFT" deixada sem preencher em schedule/legenda. |
| 4 | Clearance de porta | Porta de passagem (swing/pocket) abaixo da largura mínima de código: 34" pra swing, 32" pra pocket. Só verifica tipos claramente de passagem (SWING, DOUBLE, INVISIBLE, POCKET). |
| 5 | Sequência de revisão | Duas checagens no quadro de revisão de cada prancha: (a) os números de revisão precisam ser uma sequência sem buraco; (b) a data de uma revisão não pode ser anterior à da revisão de antes. |
| 6 | Cota não resolvida (TBD) em demolição/construção/reforço | Nota de demolição, construção ou reforço que usa uma dessas palavras-chave mas deixa a cota como "TBD" em vez de um número resolvido. |
| 7 | Altura de teto (código x Ceiling Schedule) | O código de teto carimbado na planta (ex.: "CE04" sobre "132\" A.F.F.") precisa bater com a altura da mesma linha de código no Ceiling Schedule. |
| 8 | Quantidade de luminária (só pacotes Revit) | Quantas vezes um código de luminária aparece de fato no RCP/Lighting/Circuits comparado com a quantidade do Fixture Schedule. Só funciona em pacotes Revit — AutoCAD não tagueia cada luminária individualmente. |
| 10 | Porta sem linha no Door Schedule | Tag de porta na planta (ex.: "D10") que não existe no Door Schedule. Os códigos válidos são aprendidos do próprio schedule do pacote. *(Trazo: Nook & David)* |
| 11 | Código da planta x legenda da mesma prancha | (a) Código marcado na planta (FL15, CE07…) sem linha na legenda/schedule da prancha; (b) linha da legenda que não aparece em nenhum lugar da planta — geralmente sobra do outro andar. *(Trazo: Hibiscus, Nook & David)* |
| 12 | Altura de teto entre pranchas | Extensão da regra 7: pranchas sem Ceiling Schedule (Lighting, Circuits, Flooring, Proposed) também são comparadas com o schedule do pacote. *(Trazo: Guerra, Height)* |
| 13 | Altura não resolvida "H=XX" | Nota de outlet/switch/keypad com altura de instalação ainda como placeholder. *(Trazo: Hibiscus, Height)* |
| 14 | ROUGH OPENING em drywall | Nota de rough opening associada a drywall — rough opening é madeira a madeira (2x4). *(Trazo: Height · Dell Anno)* |
| 15 | LED como "outlet" | Nota pedindo outlet/receptacle para LED em vez de "PIGTAIL CONNECTION CONTROLLED BY WALL SWITCH". *(Trazo: Height · Idelli)* |
| 16 | Nota de quantidades por andar | (a) Nota "QUANTITIES ABOVE REFER TO THE …FLOOR ONLY" citando o andar errado; (b) prancha de andar com quantidades sem essa nota, quando o pacote usa a convenção. *(Trazo: Hibiscus)* |
| 17 | Endereço no carimbo | Prancha com endereço do projeto diferente do resto do pacote (prancha reaproveitada de outro projeto). *(Trazo: Nook & David)* |

Typos sistêmicos (regra 1) ganharam: HARWARE, THICKNEES, WASJING, BDIDET, SWITCES, LANDSCAPPING.

## Revisão visual entre pranchas (regras do Trazo)

As regras abaixo dependem de enxergar o desenho (bubbles, cores, hatches, cotas, alinhamentos) e de comparar pranchas relacionadas, então rodam numa camada visual com Claude (`qc_engine/visual_review.py`): cada prancha é renderizada e as pranchas da mesma disciplina e do mesmo andar vão juntas numa chamada (ex.: RCP + Lighting + Circuits do 1º andar). Achados vêm como evidência **Visual**, confiança Média ou Menor, com o ID da regra.

- Liga sozinha quando `ANTHROPIC_API_KEY` está configurada no Render. Para desligar: `QC_VISUAL_RULES=off`. Modelo: `QC_VISUAL_MODEL` (padrão `claude-sonnet-4-5`).
- Catálogo completo (80 regras, com origem de cada uma): `qc_engine/data/trazo_rules.json`. As 9 que o motor de texto já cobre ficam fora da camada visual para não duplicar.
- Fonte: 642 tasks e comentários de 73 boards em 11 projetos do Trazo (leitura apenas, nov/2026).

| Grupo | Regras |
|---|---|
| Todas as pranchas | **C04** Cor de acabamento na legenda bate com a cor usada na planta.<br>**C06** Porta/parede presente em uma planta aparece em todas (Proposed, Construction, Flooring, RCP).<br>**C09** Quantidades da legenda batem com a contagem em planta.<br>**C13** Especificação de material na legenda correta para o ambiente.<br>**C15** Desenho coerente com o 3D aprovado (alinhamentos, posições, acabamentos).<br>**R01** Todo item NOVO (jbox, outlet, LED, power supply, quantidade alterada) está bubbled.<br>**R02** Item apenas RELOCADO não recebe bubble de novo.<br>**R03** Mudanças de acabamento pertinentes ao GC bubbled na legenda.<br>**R04** Mudança de tamanho (curtain pockets, window treatment) bubbled + nota do que mudou.<br>**R05** Correção feita em revisão nova e mantida bubbled nas revisões seguintes.<br>**G01** Vermelho pontilhado = reforço de teto; não reutilizar para outra coisa.<br>**G02** Azul pontilhado = dropped ceiling / cove novo.<br>**G03** Roxo = blackout rollers (por dentro da janela).<br>**G04** Cores não se confundem e não mudam de significado entre andares.<br>**G05** Hatches de tadelakt/demolição visíveis.<br>**G06** Furniture layer ligado no RCP geral; desligado em lighting, ceiling e flooring.<br>**G07** Itens do outro andar em cinza claro com nota.<br>**G09** Espaçamento igual entre itens de legenda. |
| Original / Proposed / Construction | **R06** Itens opcionais com nota 'PLEASE PROVIDE PRICE SEPARATELY FOR CLIENT APPROVAL'.<br>**R07** Demolição indicada (hatch + nota) para tudo que sai: portas, paredes, portões, fixtures.<br>**R08** Existentes marcados 'EXISTING TO REMAIN'; reaproveitados com 'UNINSTALL, STORE AND RE-INSTALL'.<br>**R09** Itens de terceiros marcados 'BY OTHERS / BY AV' e fora das quantidades do GC.<br>**R10** Set do GC mostra condição de obra; acabamento final só em nota na legenda.<br>**R11** Sem itens duplicados de scope of work.<br>**D01** Shower enclosures/vidros: dimensões de painéis fixos E portas em planta, em todos os banheiros.<br>**D06** Curtain pocket com dimensão própria (sheers) e janela com dimensão própria (rollers).<br>**D08** Eixo de pia, faucet e toilet cotados.<br>**D13** Tamanho de nicho não aparece no Construction (só nos SD DS).<br>**D14** Quantidades de acabamento em SQFT, nunca W x H.<br>**N03** Circulação de cozinha com portas de geladeira ≥ 42". |
| Flooring / Baseboard | **F01** Baseboard da área seca no mesmo material do piso; altura = step do shower.<br>**F02** Perfil metálico entre pisos indicado; legenda de baseboard (ex.: METALLIC REVEAL 3/4").<br>**F03** Furniture layer desligado no Flooring; hatch de piso claro.<br>**F04** Paginação de tile atualizada para o tamanho especificado (ex.: 24" x 48"). |
| RCP / Lighting / Ceiling / Circuits | **C01** Todo item removido/adicionado no RCP aparece igual em Lighting, Ceiling e Circuits (ex.: sconce eliminada que ainda aparece).<br>**C02** Todo bubble do Lighting e do Ceiling se repete nas outras plantas afetadas.<br>**C03** Item marcado como 'removed' não continua desenhado em nenhuma planta.<br>**C10** Pé-direito duplo: sem cor no 1º andar (só C.H.); cor do teto na planta do 2º andar.<br>**C11** Tetos de alturas diferentes nunca com a mesma cor; coves com cor e altura próprias na legenda.<br>**C12** Dropped ceiling do arquiteto representado (pontilhado azul) com alturas iguais ao set do arquiteto.<br>**D02** Exhaust fan cotado da parede (padrão 12" ao centro).<br>**D03** Luzes de canto de shower a 8" x 8".<br>**D04** Luzes ao longo de curtain pocket cotadas do pocket (ex.: 18.5").<br>**D05** Tracks de luz com cotas de posicionamento.<br>**D12** Pontos LED de fornecedores NÃO cotados no set do GC.<br>**E01** Linhas do mesmo circuito sempre conectadas; luz em 2 switches = linhas juntas.<br>**E02** Não juntar no mesmo circuito luzes em tetos de alturas diferentes.<br>**E03** Jbox de pendente em circuito separado.<br>**E04** Toda luz tem símbolo E sigla; todo LED tem circuito e switch.<br>**E05** LED sob vanity presente; pigtail do espelho no mesmo circuito do LED da vanity.<br>**E06** Medicine cabinets de 2 fornecedores = 2 pigtails separados.<br>**E08** Power para drapery em todos os curtain pockets, bubbled.<br>**E14** Luminárias decorativas pesadas com specs enviados ao GC (reforço de teto).<br>**E15** Fog glass elétrico = power de AV (low voltage).<br>**E17** Speakers fora de ceiling cove. |
| Outlets | **E09** Nunca switch na lateral de marcenaria.<br>**E10** Outlets sobre marcenaria em cor diferente; ponto de piso dentro da marcenaria.<br>**E11** Outlets distinguem EXISTENTE / RELOCADO / NOVO com representação própria.<br>**E12** Outlet alta do hood presente.<br>**E13** Outlets/switches posicionados com blocos de mobiliário corretos ligados.<br>**E16** Keypads sem conflito com batente, centralizados, H=48".<br>**E18** Notas padrão: supply & install de todas, screwless, floor caps, 5 extras no orçamento. |
| Doors / Hardware | **P02** Schedule com colunas ROOM, DOOR FINISH, HINGE TYPE, HANDLE/LOCK TYPE, HARDWARE FINISH, OPENING DIRECTION.<br>**P03** Lock em quartos e banheiros; passage em closets e AC doors.<br>**P04** Frameless vs framed consistente com a regra do projeto.<br>**P05** Porta externa/garagem: frame externo, frameless interno, casing especial.<br>**P06** Linha pontilhada acima de portas.<br>**P07** Pocket door nova com nota de reframing.<br>**P08** Painéis de vidro fixos com altura na legenda e dimensões em planta.<br>**N01** Toilet: mínimo 32" de clearance.<br>**P09** Pivot/porta mantém 32" de clearance. |

## Regra opcional (você escolhe quando ligar)

| # | Regra | O que verifica | Como ativar |
|---|-------|-----------------|--------------|
| 9 | Especificação não resolvida (TBD) | Uma célula de schedule/legenda com o valor de acabamento/material deixado só como "TBD". | Marque "Verificar specs TBD" ao anexar o PDF na timeline do projeto (aba Projetos). Fica desligada por padrão porque TBD é normal em early stage. |

## Regras removidas (testadas e descartadas)

- **Spec de porta incompleta** (colunas do Door Schedule em branco) — removida porque às vezes a spec realmente ainda não existe, e a regra virava ruído.

## Regras propostas (preencha aqui)

Formato sugerido — mas pode escrever do seu jeito, eu entendo:

- **Nome da regra:**
  **O que verificar:**
  **Onde já vi isso dar problema (prancha/projeto real, se tiver):**
  **Alguma exceção conhecida:**

<!-- adicione as próximas regras abaixo desta linha -->
