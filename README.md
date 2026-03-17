```markdown
# 📊 etl-vendas-bigquery

Pipeline de dados em Python para extração de planilhas de vendas, tratamento de dados com Pandas e carga incremental automática no Google BigQuery.

## 🚀 O que este projeto faz?

Este script realiza um processo completo de **ETL (Extração, Transformação e Carga)**:
1. **Extração:** Acessa uma URL dinâmica e faz o download de uma base de vendas em formato Excel (`.xlsx`).
2. **Transformação:** Utiliza a biblioteca `pandas` para limpar os dados, expandir colunas que contêm dicionários aninhados (JSON/Dict) e corrigir os tipos de dados (Datas, Inteiros, Booleanos e Strings).
3. **Carga Incremental:** Conecta-se ao Google BigQuery, verifica qual foi a última data de pedido inserida na tabela e **carrega apenas os dados novos**, evitando duplicidade e otimizando custos.

## 🛠️ Tecnologias Utilizadas

* **Python 3**
* **Pandas & Openpyxl**: Para processamento e leitura de arquivos Excel na memória.
* **Google Cloud BigQuery**: Data Warehouse de destino dos dados.
* **Requests**: Para consumo do link de download da planilha.

## ⚙️ Como configurar e rodar

### 1. Instale as dependências
Abra o seu terminal e instale as bibliotecas necessárias para rodar o projeto localmente:
```bash
pip install pandas openpyxl requests google-cloud-bigquery
```

### 2. Configuração do Google Cloud (BigQuery)
Para que o script funcione, você precisa ter um projeto no Google Cloud:
1. Crie um Dataset e uma Tabela no BigQuery.
2. Crie uma **Conta de Serviço (Service Account)** com permissões para editar o BigQuery (BigQuery Data Editor / BigQuery User).
3. Baixe a chave dessa conta de serviço no formato **JSON**.

### 3. Configurando a Autenticação (Variável de Ambiente)
O código busca as credenciais de forma segura através de uma variável de ambiente chamada `BQ_KEY_JSON`. 

* **Para rodar no seu computador:** Crie a variável de ambiente `BQ_KEY_JSON` contendo todo o texto do arquivo JSON baixado do Google Cloud.
* **Para rodar no GitHub Actions:** Vá até as configurações do seu repositório (`Settings` > `Secrets and variables` > `Actions`), clique em *New repository secret*, defina o nome como `BQ_KEY_JSON` e cole o conteúdo do arquivo JSON.

### 4. Executando o Script
Com as variáveis de ambiente configuradas e os nomes do seu Projeto/Dataset atualizados no código, basta rodar:
```bash
python etl-venda.py
```
O console mostrará o passo a passo, a identificação da última data inserida no BigQuery e o total de linhas novas adicionadas.
