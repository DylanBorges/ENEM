# Banco de questões TRI

O endpoint público `GET /v1/questions` reúne os itens ativos associados a cadernos e a uma calibração publicada. Ele não cria parâmetros psicométricos. No banco local atual, 1.638 itens de 2017 a 2025 possuem parâmetro `b` publicado; itens anulados ou sem parâmetros não aparecem neste catálogo TRI.

Filtros: `year`, `area` (`LC`, `CH`, `CN`, `MT`), `subject`, `difficulty` (`facil`, `media`, `dificil`), `page` e `page_size`. A resposta inclui paginação, totais, anos disponíveis e disciplinas verificadas.

## Dificuldade

Para cada edição e área, o endpoint ordena os valores reais de `b` dos itens publicados e divide a lista em três partes aproximadamente iguais. A faixa é **relativa ao mesmo ano e área**; fácil/média/difícil não são categorias oficiais do Inep nem uma nota do estudante. Nenhum parâmetro `a`, `b` ou `c` é inferido ou preenchido quando falta nos microdados.

## Disciplina

Os microdados identificam a área e a habilidade, não a disciplina específica. O catálogo só atribui automaticamente Matemática aos itens `MT` e Inglês/Espanhol aos cinco itens de língua estrangeira identificados pelo caderno. Os demais ficam sem classificação em vez de receber rótulos como Biologia ou História sem conferência do enunciado. O filtro de disciplina apresenta apenas rótulos efetivamente verificados. O total classificado aparece na interface.

## Caderno oficial

Cada cartão abre o PDF oficial do Inep. O arquivo `services/api/app/db/question_pages.json` contém apenas os números de página extraídos dos PDFs locais de 2017 a 2025, incluindo as páginas alternativas de Inglês e Espanhol. Para atualizar após adicionar novos cadernos, execute `python -m pipelines.inep.map_question_pages` na raiz do projeto e revise a cobertura antes de publicar. O texto integral das questões e as imagens permanecem nos PDFs do Inep.
