import json
from pathlib import Path

file_path = Path('main.ipynb')
nb = json.loads(file_path.read_text(encoding='utf-8'))

cell_id_to_replace = '#VSC-ba82d8db'
idx = next(i for i, c in enumerate(nb['cells']) if c.get('id') == cell_id_to_replace)

relative_paths = [
    'listaEscolasDFInep.csv',
    'Estatistica_Censo_Escolar/Tabela Dinâmica - Localidade por 2 Categorias.csv',
    'Catalogo_Escola/Análise - Tabela da lista das escolas - Detalhado.csv',
    'Censo_2022_IBGE/5_17_anos_frequencia/tabela10058_br_uf.ods',
    'Censo_2022_IBGE/Taxa_bruta_de_frequencia/tabela10056_br_uf.ods',
    'Censo_2022_IBGE/media_anos_estudo/tabela10062_br_uf.ods',
    'Censo_2022_IBGE/pessoas_superior_completo_idade/tabela10064_br_uf.ods',
    'Censo_2022_IBGE/maior_18_instrucao/tabela10061_br_uf.ods',
    'Censo_2022_IBGE/maior_18_frequencia/tabela10059_br_uf.ods',
    'Censo_2022_IBGE/pessoas_nivel_superior_completo_sexo_raca/tabela10065_br_uf.ods',
    'Censo_2022_IBGE/ate_5_anos_frequencia/tabela10057_br_uf.ods',
    'Censo_2022_IBGE/indicadores_censo/Censo 2022 - Alfabetização - Brasil.csv',
    'Censo_2022_IBGE/indicadores_censo/Censo 2022 - Alfabetização de indígenas - Brasil.csv',
    'Censo_2022_IBGE/indicadores_censo/Censo 2022 - Alfabetização de moradores por espécie de domicílio - Brasil.csv',
    'Censo_2022_IBGE/indicadores_censo/Censo 2022 - Número médio de anos de estudo, por sexo - Brasil.csv',
    'Censo_2022_IBGE/indicadores_censo/Censo 2022 - Número médio de anos de estudo, por cor ou raça - Brasil.csv',
    'Censo_2022_IBGE/indicadores_censo/Censo 2022 - Pessoas com nível superior completo, por área de formação - Brasil.csv',
    'Censo_2022_IBGE/indicadores_censo/Censo 2022 - Porcentagem de alfabetizados na população total e em favelas - Brasil.csv',
    'Censo_2022_IBGE/indicadores_censo/Censo 2022 - Taxa de alfabetização por grupos de idade - Brasil.csv',
    'Censo_2022_IBGE/indicadores_censo/Censo 2022 - Taxa de alfabetização por sexo e cor ou raça - Brasil.csv',
    'Censo_2022_IBGE/indicadores_censo/Censo 2022 - Taxa bruta de frequência escolar, por grupo de idade - Brasil.csv',
]

new_cells = []
new_cells.append({
    'cell_type': 'code',
    'execution_count': None,
    'metadata': {},
    'outputs': [],
    'source': [
        'pd.set_option("display.max_columns", None)\n\n'
        'print("File: listaEscolasDFInep.csv")\n'
        'display(dataframes["listaEscolasDFInep.csv"].head(20))\n'
    ],
})

for path in relative_paths[1:]:
    source = (
        f'print("File: {path}")\n'
        f'display(dataframes["{path}"].head(20))\n'
    )
    new_cells.append({
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': [source],
    })

nb['cells'] = nb['cells'][:idx] + new_cells + nb['cells'][idx+1:]
file_path.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print('Notebook updated')
