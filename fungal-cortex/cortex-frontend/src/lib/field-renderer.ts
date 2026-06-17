/** WebGL field renderer — renders Stigmergy field textures. */

const VERTEX_SHADER = `#version 300 es
in vec2 a_position;
in vec2 a_texcoord;
out vec2 v_texcoord;
void main() {
  gl_Position = vec4(a_position, 0.0, 1.0);
  v_texcoord = a_texcoord;
}`;

const FRAGMENT_SHADER = `#version 300 es
precision highp float;
in vec2 v_texcoord;
uniform sampler2D u_signal;
uniform sampler2D u_nutrient;
uniform sampler2D u_damage;
uniform sampler2D u_temperature;
uniform int u_activeLayer;
uniform float u_time;
out vec4 outColor;

vec3 sigColor(float v) { return mix(vec3(0.05,0.02,0.1), vec3(0.9,0.15,0.3), v); }
vec3 nutColor(float v) { return mix(vec3(0.02,0.05,0.02), vec3(0.15,0.85,0.25), v); }
vec3 damColor(float v) { return mix(vec3(0.05,0.05,0.08), vec3(0.5,0.5,0.55), v); }
vec3 tempColor(float v) { return mix(vec3(0.02,0.05,0.1), vec3(1.0,0.6,0.1), v); }

void main() {
  float s = texture(u_signal, v_texcoord).r;
  float n = texture(u_nutrient, v_texcoord).r;
  float d = texture(u_damage, v_texcoord).r;
  float t = texture(u_temperature, v_texcoord).r;

  vec3 col;
  if (u_activeLayer == 0) col = sigColor(s);
  else if (u_activeLayer == 1) col = nutColor(n);
  else if (u_activeLayer == 2) col = damColor(d);
  else col = tempColor(t);

  // Subtle temporal dither for organic feel
  float grain = fract(sin(dot(v_texcoord, vec2(12.9898, 78.233))) * 43758.5453 + u_time * 0.1) - 0.5;
  col += grain * 0.02;

  outColor = vec4(col, 1.0);
}`;

const LAYER_INDEX: Record<string, number> = {
  signal: 0,
  nutrient: 1,
  damage: 2,
  temperature: 3,
};

export interface FieldTextures {
  signal: WebGLTexture;
  nutrient: WebGLTexture;
  damage: WebGLTexture;
  temperature: WebGLTexture;
}

export class FieldRenderer {
  private gl: WebGL2RenderingContext;
  private program: WebGLProgram;
  private textures: FieldTextures | null = null;
  private animationId: number = 0;
  private width: number;
  private height: number;
  private activeLayer: number = 0;
  private time: number = 0;

  constructor(canvas: HTMLCanvasElement) {
    const gl = canvas.getContext("webgl2", { premultipliedAlpha: false });
    if (!gl) throw new Error("WebGL2 not available");
    this.gl = gl;
    this.width = canvas.width;
    this.height = canvas.height;

    this.program = this.compileProgram(VERTEX_SHADER, FRAGMENT_SHADER);
    this.setupGeometry();
  }

  private compileProgram(vs: string, fs: string): WebGLProgram {
    const gl = this.gl;
    const compile = (src: string, type: number): WebGLShader => {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
        const log = gl.getShaderInfoLog(s);
        gl.deleteShader(s);
        throw new Error(`Shader compile error: ${log}`);
      }
      return s;
    };
    const prog = gl.createProgram()!;
    gl.attachShader(prog, compile(vs, gl.VERTEX_SHADER));
    gl.attachShader(prog, compile(fs, gl.FRAGMENT_SHADER));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      throw new Error(`Program link error: ${gl.getProgramInfoLog(prog)}`);
    }
    return prog;
  }

  private setupGeometry(): void {
    const verts = new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]);
    const texcoords = new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]);
    this.bufferData("a_position", verts, 2);
    this.bufferData("a_texcoord", texcoords, 2);
  }

  private bufferData(name: string, data: Float32Array, size: number): void {
    const gl = this.gl;
    const loc = gl.getAttribLocation(this.program, name);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
  }

  private createTexture(data: Float64Array): WebGLTexture {
    const gl = this.gl;
    const tex = gl.createTexture()!;
    const pixels = new Uint8Array(data.length);
    for (let i = 0; i < data.length; i++) {
      pixels[i] = Math.round(data[i] * 255);
    }
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texImage2D(
      gl.TEXTURE_2D, 0, gl.R8, this.width, this.height, 0,
      gl.RED, gl.UNSIGNED_BYTE, pixels
    );
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return tex;
  }

  updateTextures(fields: {
    signal: Float64Array;
    nutrient: Float64Array;
    damage: Float64Array;
    temperature: Float64Array;
  }): void {
    const gl = this.gl;
    if (this.textures) {
      gl.deleteTexture(this.textures.signal);
      gl.deleteTexture(this.textures.nutrient);
      gl.deleteTexture(this.textures.damage);
      gl.deleteTexture(this.textures.temperature);
    }
    this.textures = {
      signal: this.createTexture(fields.signal),
      nutrient: this.createTexture(fields.nutrient),
      damage: this.createTexture(fields.damage),
      temperature: this.createTexture(fields.temperature),
    };
  }

  setLayer(layer: string): void {
    this.activeLayer = LAYER_INDEX[layer] ?? 0;
  }

  start(): void {
    const gl = this.gl;
    const render = () => {
      this.time += 0.016;
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.useProgram(this.program);

      if (this.textures) {
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, this.textures.signal);
        gl.uniform1i(gl.getUniformLocation(this.program, "u_signal"), 0);
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, this.textures.nutrient);
        gl.uniform1i(gl.getUniformLocation(this.program, "u_nutrient"), 1);
        gl.activeTexture(gl.TEXTURE2);
        gl.bindTexture(gl.TEXTURE_2D, this.textures.damage);
        gl.uniform1i(gl.getUniformLocation(this.program, "u_damage"), 2);
        gl.activeTexture(gl.TEXTURE3);
        gl.bindTexture(gl.TEXTURE_2D, this.textures.temperature);
        gl.uniform1i(gl.getUniformLocation(this.program, "u_temperature"), 3);
      }

      gl.uniform1i(gl.getUniformLocation(this.program, "u_activeLayer"), this.activeLayer);
      gl.uniform1f(gl.getUniformLocation(this.program, "u_time"), this.time);

      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      this.animationId = requestAnimationFrame(render);
    };
    this.animationId = requestAnimationFrame(render);
  }

  stop(): void {
    cancelAnimationFrame(this.animationId);
  }

  resize(w: number, h: number): void {
    this.width = w;
    this.height = h;
    this.gl.viewport(0, 0, w, h);
  }

  destroy(): void {
    this.stop();
    if (this.textures) {
      const gl = this.gl;
      gl.deleteTexture(this.textures.signal);
      gl.deleteTexture(this.textures.nutrient);
      gl.deleteTexture(this.textures.damage);
      gl.deleteTexture(this.textures.temperature);
    }
    this.gl.deleteProgram(this.program);
  }
}
