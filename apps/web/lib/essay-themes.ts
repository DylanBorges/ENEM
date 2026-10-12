export type EssayTheme = {
  id: string;
  title: string;
  texts: readonly [{ title: string; body: string }, { title: string; body: string }];
};

// Propostas e textos originais para treino; não são temas nem excertos do Inep.
export const essayThemes: readonly EssayTheme[] = [
  {
    id: "educacao-midiatica",
    title: "Desafios para fortalecer a educação midiática no Brasil",
    texts: [
      { title: "Informação e escolha", body: "Uma notícia pode chegar a milhões de pessoas antes que sua origem seja verificada. Saber reconhecer autoria, contexto e intenção ajuda o leitor a decidir o que merece confiança e o que precisa ser investigado." },
      { title: "Aprender a verificar", body: "A educação midiática pode fazer parte da rotina escolar e da vida adulta. Comparar fontes, observar datas e distinguir opinião de fato são práticas que dependem de acesso à informação e de oportunidades de aprendizagem." },
    ],
  },
  {
    id: "residuos-urbanos",
    title: "Caminhos para reduzir o descarte inadequado de resíduos nas cidades brasileiras",
    texts: [
      { title: "Depois do consumo", body: "O destino de uma embalagem não termina quando ela sai de casa. Coleta, separação, reaproveitamento e descarte formam uma cadeia que envolve moradores, empresas e poder público." },
      { title: "Responsabilidade compartilhada", body: "Quando faltam infraestrutura e informação, materiais recicláveis podem se misturar a rejeitos. A solução exige hábitos de consumo mais conscientes e serviços acessíveis em diferentes bairros." },
    ],
  },
  {
    id: "acessibilidade-digital",
    title: "Obstáculos à acessibilidade digital para pessoas com deficiência no Brasil",
    texts: [
      { title: "Uma barreira invisível", body: "Um formulário sem rótulos claros ou um vídeo sem legenda pode impedir o uso de um serviço essencial. Barreiras digitais surgem nas escolhas de projeto e podem ser reduzidas desde a criação da ferramenta." },
      { title: "Participação", body: "Tecnologia acessível amplia possibilidades de estudo, trabalho e participação social. Para que isso aconteça, é preciso considerar diferentes formas de perceber, compreender e interagir com conteúdos digitais." },
    ],
  },
  {
    id: "idosos-cidade",
    title: "Desafios para garantir a participação social das pessoas idosas nas cidades brasileiras",
    texts: [
      { title: "Circular pela cidade", body: "Calçadas, transporte, espaços culturais e serviços públicos influenciam a autonomia de quem envelhece. Uma cidade acolhedora considera diferentes ritmos de deslocamento e formas de acesso." },
      { title: "Além do cuidado", body: "A participação das pessoas idosas não se limita ao atendimento de saúde. Convivência, aprendizado e decisões coletivas também fazem parte do direito de viver a cidade." },
    ],
  },
  {
    id: "saude-mental-jovens",
    title: "A importância do acolhimento da saúde mental dos jovens no Brasil",
    texts: [
      { title: "Escuta sem julgamento", body: "Pressões por desempenho, conflitos e mudanças podem afetar a vida de adolescentes e jovens. Espaços de escuta permitem reconhecer dificuldades antes que o silêncio as torne ainda mais difíceis de enfrentar." },
      { title: "Rede de apoio", body: "Família, escola, comunidade e serviços de saúde podem atuar de forma complementar. Acolher envolve combater o estigma e tornar o apoio conhecido e acessível." },
    ],
  },
  {
    id: "patrimonio-cultural",
    title: "Caminhos para valorizar o patrimônio cultural das comunidades brasileiras",
    texts: [
      { title: "Memória viva", body: "Festas, saberes, lugares e formas de expressão ajudam uma comunidade a contar sua história. Preservar esse patrimônio também significa ouvir as pessoas que o mantêm vivo." },
      { title: "Acesso e continuidade", body: "Quando novas gerações conhecem práticas culturais do seu território, podem reinterpretá-las e mantê-las em circulação. Educação e espaços públicos têm papel nessa aproximação." },
    ],
  },
  {
    id: "seguranca-alimentar",
    title: "Desafios para ampliar o acesso à alimentação adequada no Brasil",
    texts: [
      { title: "Mais que quantidade", body: "Alimentar-se adequadamente envolve qualidade, regularidade e respeito aos hábitos culturais. Ter comida disponível em um território não significa que todas as famílias possam adquiri-la." },
      { title: "Da produção à mesa", body: "Produção, transporte, preço e desperdício afetam o acesso aos alimentos. Pensar nesse percurso ajuda a identificar ações possíveis para governos, comunidades e consumidores." },
    ],
  },
  {
    id: "mobilidade-urbana",
    title: "O papel da mobilidade urbana no acesso a oportunidades no Brasil",
    texts: [
      { title: "Tempo de deslocamento", body: "O caminho entre casa, estudo e trabalho pode consumir uma parte importante do dia. A qualidade do transporte interfere no acesso a serviços e no tempo disponível para convívio e descanso." },
      { title: "Cidade para todos", body: "Planejar a mobilidade exige olhar para pedestres, ciclistas e usuários do transporte coletivo, inclusive pessoas com mobilidade reduzida. Diferentes trajetos precisam ser possíveis e seguros." },
    ],
  },
];
