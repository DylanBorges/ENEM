"""Conservative, non-official subject hints derived from question wording."""

import re
import unicodedata

TERMS = {
    "CN": {
        "Biologia": ("celula", "genes", "gene ", "genetica", "dna", "rna", "cromossomo", "bacteria", "virus", "fungo", "ecossistema", "biodiversidade", "especie", "fotossintese", "enzima", "organismo", "evolucao", "selecao natural", "sistema imunologico", "vacina", "vegetal", "animal", "ecologia", "bioma", "reproducao sexuada"),
        "Física": ("velocidade", "aceleracao", "forca ", "forcas ", "movimento", "circuito", "corrente eletrica", "tensao eletrica", "potencia eletrica", "resistencia eletrica", "resistor", "campo magnetico", "onda", "frequencia", "lente", "espelho", "raio de luz", "energia cinetica", "energia potencial", "pressao atmosferica", "termodinamica"),
        "Química": ("molecula", "atomo", "reacao quimica", "reacoes quimicas", "elemento quimico", "ligacao quimica", "solucao aquosa", "concentracao molar", "tabela periodica", "acido", "base conjugada", "ph ", "composto organico", "hidrocarboneto", "oxidacao", "reducao", "eletron", "proton", "ion", "sais dissolvidos", "estequiometria"),
    },
    "CH": {
        "História": ("revolucao", "colonial", "colonizacao", "escravidao", "escravista", "ditadura", "regime militar", "guerra mundial", "idade media", "imperio", "republica velha", "estado novo", "seculo x", "seculo 1", "seculo 2", "antiguidade", "independencia do brasil", "periodo historico", "renascimento", "feudal", "indigena"),
        "Geografia": ("territorio", "paisagem", "cartograf", "mapa", "clima", "urbanizacao", "migracao", "relevo", "bioma", "globalizacao", "espaco geografico", "agricultura", "desmatamento", "bacia hidrografica", "populacao", "metropole", "solo", "recursos naturais", "industrializacao", "fronteira"),
        "Filosofia": ("filosofo", "filosofia", "etica", "moral", "aristoteles", "platao", "kant", "socrates", "descartes", "nietzsche", "epistemologia", "metafisica", "existencialismo", "racionalismo", "iluminismo", "teoria do conhecimento"),
        "Sociologia": ("sociologia", "sociedade", "classe social", "desigualdade", "movimento social", "relacoes sociais", "capitalismo", "trabalho assalariado", "genero", "racismo", "cidadania", "identidade cultural", "instituicao social", "cultura de massa", "poder simbolico", "durkheim", "weber", "bourdieu"),
    },
    "LC": {
        "Literatura": ("poema", "poesia", "romance", "cronica", "obra literaria", "narrador", "conto", "literatura", "personagem", "modernismo", "eu lirico", "escritor", "escritora"),
        "Artes": ("pintura", "grafite", "fotografia", "danca", "teatro", "cinema", "musica", "cancao", "artista", "obra de arte", "artes visuais", "performance", "escultura"),
        "Educação Física": ("esporte", "atletismo", "atividade fisica", "exercicio fisico", "pratica corporal", "futebol", "ginastica", "modalidade esportiva", "luta", "jogo corporal", "educacao fisica"),
    },
}


def classify_subject(area: str, text: str, position: int, language: str | None) -> str | None:
    if area == "MT":
        return "Matemática"
    if area == "LC" and position <= 5:
        return {"INGLES": "Inglês", "ESPANHOL": "Espanhol"}.get(language or "")
    normalized = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    normalized = re.sub(r"\s+", " ", normalized)
    scores = {subject: sum(term in normalized for term in terms) for subject, terms in TERMS.get(area, {}).items()}
    if not scores:
        return None
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    winner, count = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0
    if count >= 2 and count > second:
        return winner
    if area == "LC" and count == 0:
        return "Português"
    return None
