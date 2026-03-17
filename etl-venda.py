import os
import requests
import pandas as pd
import io
from urllib.parse import unquote, urlparse, parse_qs
import ast
import re
from google.oauth2 import service_account
import json
from google.cloud import bigquery
from datetime import datetime, timedelta
import numpy as np
import traceback

# Configurações
PROJETO_ID = "still-protocol-440221-k2"
DATASET_ID = "vendas_dataset"
TABELA_ID = "df_final_vendas"

def carregar_incremental_por_data(df):
    """
    Carrega dados novos garantindo tipos corretos com Schema explícito.
    """
    try:
        # 1. Autenticação (Adaptado para GitHub Actions)
        # Lê a chave guardada nos Secrets do repositório
        chave_raw = os.environ.get('BQ_KEY_JSON')
        
        if not chave_raw:
            raise ValueError("A variável de ambiente 'BQ_KEY_JSON' não foi encontrada.")
            
        info_chave = json.loads(chave_raw) if isinstance(chave_raw, str) else chave_raw
        credentials = service_account.Credentials.from_service_account_info(info_chave)
        
        # 2. Cliente BigQuery
        client = bigquery.Client(project=PROJETO_ID, credentials=credentials)
        tabela_ref = f"{PROJETO_ID}.{DATASET_ID}.{TABELA_ID}"
        
        # 3. CRIAR UMA CÓPIA
        df_processed = df.copy()
        
        # 4. CONVERSÃO DE data_pedido PARA DATETIME (SEM TZ E EM MICROSEGUNDOS)
        print("🕒 Convertendo data_pedido para datetime e ajustando precisão...")
        df_processed['data_pedido'] = pd.to_datetime(df_processed['data_pedido'], errors='coerce')
        df_processed['data_pedido'] = df_processed['data_pedido'].dt.tz_localize(None)
        df_processed['data_pedido'] = df_processed['data_pedido'].dt.floor('us')
        
        print(f"Tipo após conversão: {df_processed['data_pedido'].dtype}")
        
        # 5. VERIFICAR ÚLTIMA DATA NO BIGQUERY
        print("🔍 Verificando última data na tabela BigQuery...")
        try:
            query = f"SELECT MAX(data_pedido) as ultima_data FROM `{tabela_ref}`"
            ultima_data_df = client.query(query).to_dataframe()
            ultima_data_bq = ultima_data_df['ultima_data'].iloc[0]
            
            if pd.notna(ultima_data_bq):
                ultima_data_bq = pd.to_datetime(ultima_data_bq).tz_localize(None)
                print(f"📊 Última data encontrada: {ultima_data_bq}")
                df_novos = df_processed[df_processed['data_pedido'] > ultima_data_bq].copy()
                
                if df_novos.empty:
                    print("✅ Nenhum dado novo para carregar!")
                    return
                print(f"📈 Encontrados {len(df_novos)} registros novos")
                df_carregar = df_novos
            else:
                print("🆕 Tabela vazia, carregando todos os dados")
                df_carregar = df_processed
                
        except Exception as e:
            print(f"ℹ️ Tabela não existe ou inacessível: {e}")
            print("🆕 Assumindo carga total.")
            df_carregar = df_processed
        
        # 6. LIMPEZA DOS TIPOS RESTANTES
        print("📊 Ajustando tipos das colunas...")
        for col in df_carregar.columns:
            if col == 'data_pedido':
                continue
                
            elif col in ['raiz_id_pedido', 'valor_desconto', 'senai_play', 'valores_itens_pedido',
                        'valor_unitario_item', 'quantidade_item', 'valor_total_item', 'id_sku',
                        'id_curso']:
                df_carregar[col] = pd.to_numeric(df_carregar[col], errors='coerce').astype('Int64')
            
            elif col in ['utm_campaign', 'utmPartner']:
                df_carregar[col] = pd.to_numeric(df_carregar[col], errors='coerce').astype('float64')
            
            elif col in ['status_sku', 'eh_kit', 'produto_visivel', 'produto_ativo', 'showifnotavailable']:
                df_carregar[col] = df_carregar[col].map({True: True, False: False, 'True': True, 'False': False}).astype(bool)
            
            else:
                df_carregar[col] = df_carregar[col].where(pd.notnull(df_carregar[col]), None)
                df_carregar[col] = df_carregar[col].astype("string")

        # 7. CARREGAR PARA O BIGQUERY
        print(f"📤 Carregando {len(df_carregar)} registros para o BigQuery...")
        
        job_config = bigquery.LoadJobConfig(
            create_disposition="CREATE_IF_NEEDED",
            write_disposition="WRITE_APPEND",
            autodetect=False, 
            schema=[
                bigquery.SchemaField("data_pedido", "TIMESTAMP"),
            ]
        )
        
        chunk_size = 10000
        total_chunks = (len(df_carregar) + chunk_size - 1) // chunk_size
        
        for i, chunk_start in enumerate(range(0, len(df_carregar), chunk_size)):
            chunk_end = min(chunk_start + chunk_size, len(df_carregar))
            df_chunk = df_carregar.iloc[chunk_start:chunk_end]
            
            print(f"  Carregando chunk {i+1}/{total_chunks} ({len(df_chunk)} linhas)...")
            
            job = client.load_table_from_dataframe(
                df_chunk,
                tabela_ref,
                job_config=job_config
            )
            job.result() 
            if job.errors:
                 print(f"Erros no chunk {i+1}: {job.errors}")
                 break
        
        print(f"✅ SUCESSO! {len(df_carregar)} linhas processadas.")
        
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()

def extrair_dicionario(texto):
    if pd.isna(texto) or texto == '':
        return {}
    texto_limpo = re.sub(r'array\(\[.*?\], dtype=object\)', '[]', str(texto))
    try:
        return ast.literal_eval(texto_limpo)
    except:
        return {}

def extrair_e_carregar(url):
    try:
        query = urlparse(url).query
        params = parse_qs(query)
        link_direto = params['src'][0]
        headers = {'User-Agent': 'Mozilla/5.0'}
        resposta = requests.get(link_direto, headers=headers)
        resposta.raise_for_status()
        df = pd.read_excel(io.BytesIO(resposta.content), engine='openpyxl')
        return df
    except Exception as e:
        print(f"❌ Erro na extração: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Iniciando processo via GitHub Actions...")
    url_complexa = os.environ.get('URL_COMPLEXA')

    dados = extrair_e_carregar(url_complexa)

    if dados is not None:
        if 'market_d' in dados.columns:
            df_dicts = dados['market_d'].apply(extrair_dicionario)
            df_expandido = pd.json_normalize(df_dicts)
            df_final = pd.concat([dados.drop('market_d', axis=1), df_expandido], axis=1)
        else:
            df_final = dados
        
        carregar_incremental_por_data(df_final)
