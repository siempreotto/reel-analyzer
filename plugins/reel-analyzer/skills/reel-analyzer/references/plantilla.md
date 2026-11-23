# Plantilla del entregable

Escribe en español de LATAM, tuteando. Todo lo que afirmes del video debe salir de la evidencia
(cuadros que abriste, `analysis.json`, `timeline.md`). Si algo no se puede saber (p. ej. no hay
transcripción), dilo en vez de inventarlo. Cita tiempos como `0:03`.

---

## 1. Ficha

| Campo | Valor |
|---|---|
| Cuenta | @cuenta (plataforma) |
| Link | … |
| Duración | NN s · vertical/horizontal |
| Métricas | vistas · likes · comentarios (— si no hay) |
| Tipo de formato | p. ej. talking head con texto en pantalla · POV · tutorial en pantalla · montaje con música · antes/después · lista/top · reacción · storytelling |
| Ritmo | N cortes · N cortes/min · toma promedio N s |

## 2. Hook (0–3 s)

- **Qué se ve:** encuadre, sujeto, movimiento, primer cuadro (¿hay acción desde el cuadro 0?).
- **Qué se dice:** la línea exacta (de la transcripción).
- **Texto en pantalla:** léelo literal de los cuadros del hook.
- **Audio:** ¿arranca con voz, música, efecto o silencio?
- **Por qué detiene el scroll:** 2–3 razones concretas (patrón de interrupción, curiosidad, promesa,
  conflicto, identidad, número específico, contradicción…). Menciona cuántas palabras tiene el hook.

## 3. Escena por escena

| # | Tiempo | Visual / encuadre / movimiento | Texto en pantalla | Voz | Audio no verbal | Función |
|---|---|---|---|---|---|---|
| 1 | 0:00–0:02 | Primer plano, cámara en mano, entra de golpe | "NO hagas esto" | "Si grabas así…" | Golpe de bajo + música baja | Hook |

**Función** usa este vocabulario: hook · contexto · problema · promesa · prueba/demostración ·
giro · paso N · payoff · CTA · loop (cierre que empata con el inicio).
**Audio no verbal**: música (sube/baja/corta), efectos (whoosh, pop, risas), silencios usados como
recurso, cambios de loudness. Usa `audio.loudness_lufs`, `audio.silencio` y `audio_global`.

## 4. Ritmo y audio

- Cortes/min y toma promedio, y cómo cambia el ritmo (¿se acelera hacia el final?).
- Palabras por minuto (si hay transcripción) y si la voz va pegada a los cortes.
- Música vs. voz (recuerda que `musica_probable` es una estimación), silencios y su efecto.
- Loudness integrada (las plataformas normalizan alrededor de −14 LUFS; mucho más bajo suena flojo).

## 5. Por qué funciona

3 a 5 bullets concretos, cada uno amarrado a un momento del video (tiempo + qué pasa). Nada genérico
tipo "tiene buena edición".

## 6. ADN del formato

La estructura abstracta, **sin el contenido original**, reutilizable con cualquier tema:

```
[0–3 s]  HOOK: <mecánica, p. ej. "afirmación contraintuitiva + texto grande en pantalla">
[3–8 s]  <beat>: <mecánica>
…
[final]  CTA: <mecánica>
Reglas del formato: <duración objetivo, tipo de toma, ritmo de cortes, uso de texto, audio>
```

## 7. Guion de réplica para <marca>

Guion **original** para la marca del usuario, con el mismo ADN. Nunca reutilices frases, chistes,
ejemplos ni la voz del creador original.

**Shot list**

| # | Toma | Encuadre / movimiento | Duración | Qué decir | Texto en pantalla | Audio |
|---|---|---|---|---|---|---|

**3 hooks alternativos** (respeta el número de palabras y la mecánica del hook original; ninguno
empieza con "Yo").

**Caption** (2–4 líneas + 3–5 hashtags del nicho).

**CTA** corto y honesto: no prometas enviar algo ("comenta X y te lo mando") si la marca no tiene ese
entregable y una automatización que lo envíe.

**Lista de producción**: locación, vestuario/props, equipo (luz, micrófono), qué grabar como
B-roll, plantilla de texto en pantalla, música sugerida (tipo y BPM, no un tema con derechos
específico), tiempo estimado de grabación y edición.

---

## Modo rápido

Solo: Ficha · Hook · ADN del formato · Guion corto (shot list + 1 hook alterno + CTA).

## Varios videos (comparativo)

Después de cada desglose (en modo rápido salvo que pidan completo), cierra con:

| Patrón | Video 1 | Video 2 | Video 3 |
|---|---|---|---|
| Tipo de hook | | | |
| Duración / cortes por min | | | |
| Texto en pantalla | | | |
| Audio | | | |
| CTA | | | |

Y 3–5 **patrones comunes** + un **ADN combinado** y un guion de réplica que use lo mejor de cada uno.
