# Calibração e Release Gates

## Parâmetros de itens do ENEM 2024 e 2025

As aplicações regulares disponíveis de 2024 e 2025 utilizam os parâmetros `a`, `b`, `c` que constam de `ITENS_PROVA_2024.csv` e `ITENS_PROVA_2025.csv`, publicados pelo Inep. O produto não os reestima nesse fluxo. Questões marcadas como `IN_ITEM_ABAN=1` são excluídas da estimação, mesmo quando há alternativa no gabarito. A transformação da proficiência para a nota exibida é ajustada separadamente para cada edição com resultados observados e sempre identificada como estimativa não oficial. Os protocolos e as métricas ficam em `data/processed/2024/validacao_notas_selecionadas.json` e `data/processed/2025/validacao_notas_regulares.json`. Em 2024, apenas o primeiro e o segundo dias do caderno azul foram publicados no simulador.

## Algoritmo Marginal Maximum Likelihood / EM experimental

O pipeline experimental de calibração local dos parâmetros dos itens utiliza o algoritmo de Bock & Aitkin (1981):
1. **E-step**: Cálculo das probabilidades a posteriori para os nós de quadratura;
2. **M-step**: Maximização da log-verossimilhança esperada com restrições nos parâmetros ($a \in [0.2, 3.5]$, $b \in [-4.0, 4.0]$, $c \in [0.0, 0.40]$);
3. Diagnóstico de convergência e sinalização de itens patológicos.

## Divisão de Amostra Anti-Leakage

Para uma calibração local futura, os microdados devem ser divididos estritamente em:
- **70% Calibração**: Utilizados no MML/EM para encontrar $a, b, c$;
- **15% Linking**: Utilizados para ajustar $\alpha$ e $\beta$ contra as notas oficiais;
- **15% Holdout Intocado**: Reservados exclusivamente para avaliação final das métricas de erro.

Nas validações de 2024 e 2025, os 70% ficaram reservados porque os parâmetros vieram do Inep. Os 15% de ligação e os 15% de holdout foram separados por hash determinístico dentro da amostra de cada ano. Esse holdout testa o ajuste de escala deste produto, mas não é independente da estimação original dos parâmetros pelo Inep.

## Release Gate

Nenhuma calibração pode ser publicada sem aprovação no release gate:
- MAE $\le 35$ pontos na nota final;
- Correlação de Pearson $\ge 0.85$;
- Análise de caudas (decis D1 e D10).
