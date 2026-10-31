# Blender — receitas testadas

Para forma orgânica ou estilizada (caso B de `limites.md`). Medida exata, rosca e
encaixe vão para o Fusion: aqui é malha, sem parâmetros.

Tudo rodado no Blender 5.2.3 LTS, com `--background`, e fatiado de ponta a ponta.

---

## Duas formas de rodar

**Com o MCP oficial do Blender Lab** (Blender 5.1+): `execute_blender_code` roda o
script, e `get_objects_summary` prova que a conexão está de pé. Dá para capturar a
tela com `get_screenshot_of_area_as_image`. Instalação em `agentes.md`.

**Só com terminal:** grave o script e rode, sem janela:

```
blender.exe --background --factory-startup --python-exit-code 1 --python peca.py
```

O caminho do Blender vem de `scripts/detectar_modeladores.py`. O script salva o
`.blend`, e o usuário abre esse arquivo para ver a peça.

---

## A peça é um script

Malha não tem histórico paramétrico. Por isso a peça é **um script rerodável, com
os parâmetros no topo**. Ajuste é mudar o número e rodar de novo, do começo:
`preparar_cena()` apaga tudo. Guarde o script ao lado do `.blend`.

```python
import sys
sys.path.insert(0, r"<pasta da skill>/helpers")

import bmesh, bpy
from mathutils import Matrix
import blender_3mf as b

CAMADA = 0.12
RAIO = 15.0
COR_CORPO = "#e8b647"
COR_OLHO = "#222222"


def esfera(nome, raio, centro, cor, escala=(1, 1, 1), sub=3):
    malha = bpy.data.meshes.new(nome)
    bm = bmesh.new()
    matriz = Matrix.Translation(centro) @ Matrix.Diagonal((*escala, 1))
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=raio, matrix=matriz)
    bm.to_mesh(malha)
    bm.free()
    objeto = bpy.data.objects.new(nome, malha)
    bpy.context.collection.objects.link(objeto)
    b.colorir(objeto, cor)
    return objeto


b.preparar_cena()
corpo = esfera("slot1_corpo", RAIO, (0, 0, RAIO), COR_CORPO, (1, 0.8, 1))
```

`preparar_cena()` deixa a cena em milímetros: 1 unidade vale 1 mm. `subdivisions`
baixo dá o visual low-poly.

---

## Contrato

O mesmo do Fusion, porque o resto do fluxo depende dele:

- **Cada cor é um objeto**, com nome `slotN_descricao`, N de 1 a 4.
- **Material `cor_#rrggbb`**, com `b.colorir(objeto, "#e8b647")`. A cor do arquivo
  vem do nome do material.
- Objetos do mesmo `slotN_` podem se sobrepor: viram cascas da mesma cor.
- **Cores diferentes não se sobrepõem.** Encostar pode; dividir volume é defeito.

Malha fechada é obrigação do slicer. Primitivas fechadas e modificadores booleanos
costumam manter isso; extrusão solta e face apagada, não.

---

## Encaixar uma cor em outra

Olho na cabeça sobrepõe volume, e a validação recusa. Recorte com booleana no corpo
que recebe o encaixe:

```python
cabeca = esfera("slot1_cabeca", 9, (12, 0, 25), COR_CORPO)
olho = esfera("slot2_olho", 2, (19, 4, 27), COR_OLHO, sub=2)
recorte = cabeca.modifiers.new("olho", "BOOLEAN")
recorte.operation = "DIFFERENCE"
recorte.object = olho
```

Peça que precisa de base plana para aderir à mesa: recorte a parte de baixo com um
cubo, ou apoie sobre um disco no mesmo slot. Esfera toca a mesa num ponto e descola.

---

## Validar (passo 1c)

```python
resultado = b.validar()
b.imprimir_json(resultado)
```

Precisa dar `ok: true`. `validar()` confere contrato, material, malha fechada, volume,
limite da máquina, cor única por slot e sobreposição entre cores, sempre na malha com
modificadores aplicados. Fora da A1, passe os valores de `maquina`:
`b.validar(max_slots=4, limite_mm=175)`, e o mesmo em `b.exportar()`. A lista `erros` diz o que corrigir. A linha sai no console
com o prefixo `RESULTADO`.

Altura em múltiplo de camada não é cobrada aqui: em forma curva não existe. Avise na
mensagem se houver detalhe fino, porque traço abaixo de 0,8 mm não sai.

---

## Salvar e exportar

Passo 1: salve a cena, para o usuário abrir. Passo 3, só com o OK:

```python
b.salvar(r"<pasta_saida>/<nome-da-peca>.blend")   # passo 1
relatorio = b.exportar(r"<pasta_saida>/<nome-da-peca>.3mf")   # passo 3
b.imprimir_json(relatorio)
```

`exportar()` valida de novo e recusa cena com erro. Daí em diante é igual ao Fusion:
`scripts/fatiar.py` no passo 4.
