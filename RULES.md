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
