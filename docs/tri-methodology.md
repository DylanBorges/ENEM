# Metodologia TRI: Modelo 3PL e Estimador EAP

## Modelo Logístico de Três Parâmetros (3PL)

A probabilidade de um participante com habilidade latente $\theta$ responder corretamente ao item $i$ é dada por:

$$P_i(\theta) = c_i + (1 - c_i) \frac{1}{1 + \exp[-D a_i (\theta - b_i)]}$$

Onde:
- $\theta$: habilidade latente do estudante;
- $a_i > 0$: parâmetro de discriminação do item;
- $b_i$: parâmetro de dificuldade (localização na escala latente);
- $0 \le c_i < 1$: assíntota inferior (probabilidade de acerto ao acaso);
- $D$: constante métrica ($D=1.0$).

## Estimador Expected A Posteriori (EAP)

O estimador Bayesiano EAP calcula a esperança matemática da distribuição a posteriori:

$$\widehat{\theta}_{EAP} = \frac{\int \theta L(\theta \mid \mathbf{u}) g(\theta) d\theta}{\int L(\theta \mid \mathbf{u}) g(\theta) d\theta}$$

Propriedades fundamentais no produto:
- Produz estimativa finita mesmo para padrões extremos (100% de acertos ou 0% de acertos);
- Permite derivar desvio padrão posterior ($\sigma_{posterior}$) e intervalos críveis Bayesianos de 95%;
- Integração calculada com quadratura uniforme em grade $[-4.5, 4.5]$.

## Transformação para a Escala do ENEM

A nota estimada NÃO é uma fórmula fixa $500 + 100\theta$. Para cada edição, aplicação e área, calibra-se empiricamente uma regressão linear contra as notas oficiais dos microdados:

$$\widehat{S} = \alpha_{ano, area} + \beta_{ano, area} \cdot \widehat{\theta}$$

Com $\beta > 0$.
