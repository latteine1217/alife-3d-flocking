/**
 * WebGPU Renderer for 3D Flocking Simulation
 * 
 * 核心功能：
 * - 初始化 WebGPU 設備與管線
 * - 上傳粒子資料到 GPU (positions, types)
 * - 渲染 3D 粒子點雲，支援類型著色
 * - 相機變換（view/projection matrices）
 * 
 * 效能目標：60 FPS @ N=500
 */

import { mat4 } from 'gl-matrix';

export interface RenderData {
  positions: Float32Array;  // [x, y, z] * N
  velocities?: Float32Array; // [vx, vy, vz] * N (optional for velocity vectors)
  types: Uint8Array;        // Agent type (0=Follower, 1=Explorer, 2=Leader)
  groupLabels?: Int32Array; // Group ID for each agent (NEW)
  boxSize?: number;         // Optional: boundary box size
  resources?: Array<{       // Optional: resources to render
    position: [number, number, number];
    amount: number;
    radius: number;
    renewable: boolean;
  }>;
  groups?: Array<{          // Optional: group statistics for boundary rendering
    groupId: number;
    size: number;
    centroid: [number, number, number];
    velocity: [number, number, number];
    radius: number;
  }>;
}

export interface RendererOptions {
  enableTrails?: boolean;   // Enable velocity trails
  trailLength?: number;     // Number of history frames (default: 10)
  enableResources?: boolean; // Enable resource sphere rendering
  enableGroupBoundaries?: boolean; // Enable group boundary sphere rendering
}

export class WebGPURenderer {
  private device!: GPUDevice;
  private context!: GPUCanvasContext;
  private pipeline!: GPURenderPipeline;
  
  // GPU buffers
  private positionBuffer!: GPUBuffer;
  private typeBuffer!: GPUBuffer;
  private groupLabelBuffer!: GPUBuffer; // NEW: Group labels buffer
  private uniformBuffer!: GPUBuffer;
  private bindGroup!: GPUBindGroup;
  
  // Particle rendering (instanced quads)
  private quadVertexBuffer!: GPUBuffer; // Shared quad geometry (-1 to +1)
  
  // Render state
  private particleCount: number = 0;
  private canvas: HTMLCanvasElement | null = null;
  private particleSize: number = 0.5; // Particle radius in world units
  
  // Depth texture (persistent)
  private depthTexture!: GPUTexture;
  private depthTextureView!: GPUTextureView;
  
  // Boundary box rendering
  private boxPipeline!: GPURenderPipeline;
  private boxBuffer!: GPUBuffer;
  private boxSize: number = 50.0;
  
  // Velocity trails
  private enableTrails: boolean = true;
  private trailLength: number = 40; // History frames (~0.67 second at 60 FPS)
  private trailPipeline!: GPURenderPipeline;
  private trailBuffer!: GPUBuffer;
  private trailIndexBuffer: GPUBuffer | null = null;
  private positionHistory: Float32Array[] = []; // Circular buffer
  private currentHistoryIndex: number = 0;
  
  // Velocity vectors (arrows)
  private enableVelocityVectors: boolean = true;
  private velocityVectorPipeline!: GPURenderPipeline;
  private velocityVectorBuffer!: GPUBuffer;
  private velocityData: Float32Array | null = null;
  
  // Resource spheres
  private enableResources: boolean = true;
  private resourcePipeline!: GPURenderPipeline;
  private sphereVertexBuffer!: GPUBuffer;
  private sphereIndexBuffer!: GPUBuffer;
  private sphereIndexCount: number = 0;
  private resourceInstanceBuffer!: GPUBuffer;
  private resourceCount: number = 0;
  
  // Group coloring
  private colorMode: 'type' | 'group' = 'type'; // NEW: Color mode toggle
  
  // Group boundary spheres
  private enableGroupBoundaries: boolean = false;
  private groupSpherePipeline!: GPURenderPipeline;
  private groupSphereInstanceBuffer!: GPUBuffer;
  private groupCount: number = 0;
  
  // Group selection (for highlighting)
  private selectedGroupId: number | null = null;
  
  // Group velocity arrows
  private enableGroupVelocityArrows: boolean = false;
  private groupVelocityArrowPipeline!: GPURenderPipeline;
  private groupVelocityArrowBuffer!: GPUBuffer;
  private groupVelocityData: Array<{
    centroid: [number, number, number];
    velocity: [number, number, number];
    groupId: number;
  }> = [];
  
  /**
   * 初始化 WebGPU（adapter, device, pipeline）
   * @throws Error 如果瀏覽器不支援 WebGPU
   */
  async init(canvas: HTMLCanvasElement, options?: RendererOptions): Promise<void> {
    this.canvas = canvas;
    
    // 設定選項
    if (options) {
      this.enableTrails = options.enableTrails ?? true;
      this.trailLength = options.trailLength ?? 10;
      this.enableResources = options.enableResources ?? true;
      this.enableGroupBoundaries = options.enableGroupBoundaries ?? false;
    }
    
    // 1. 檢查 WebGPU 支援
    if (!navigator.gpu) {
      throw new Error('WebGPU not supported. Please use Chrome 113+ or Edge 113+.');
    }
    
    // 2. 請求 GPU adapter 和 device
    console.log('🔍 Requesting GPU adapter...');
    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) {
      throw new Error('Failed to get GPU adapter');
    }
    console.log('✅ GPU adapter obtained');
    
    console.log('🔍 Requesting GPU device...');
    this.device = await adapter.requestDevice();
    console.log('✅ GPU device obtained');
    
    // 3. 設定 canvas context
    console.log('🔍 Getting WebGPU canvas context...');
    this.context = canvas.getContext('webgpu') as GPUCanvasContext;
    if (!this.context) {
      throw new Error('Failed to get WebGPU canvas context');
    }
    console.log('✅ Canvas context obtained');
    
    const format = navigator.gpu.getPreferredCanvasFormat();
    console.log(`🎨 Canvas format: ${format}`);
    this.context.configure({
      device: this.device,
      format,
      alphaMode: 'premultiplied',
    });
    
    // 4. 創建 particle render pipeline
    console.log('🔍 Creating particle render pipeline...');
    this.createRenderPipeline();
    console.log('✅ Particle pipeline created');
    
    // 5. 創建 uniform buffer (128 bytes for 2x mat4)
    this.uniformBuffer = this.device.createBuffer({
      label: 'Uniform Buffer',
      size: 128, // 2 * 64 bytes (view + projection)
      usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST,
    });
    
    // 6. 創建 bind group
    const uniformBindGroupLayout = this.device.createBindGroupLayout({
      label: 'Uniform Bind Group Layout',
      entries: [
        {
          binding: 0,
          visibility: GPUShaderStage.VERTEX,
          buffer: { type: 'uniform' },
        },
      ],
    });
    
    this.bindGroup = this.device.createBindGroup({
      label: 'Uniform Bind Group',
      layout: uniformBindGroupLayout,
      entries: [
        {
          binding: 0,
          resource: { buffer: this.uniformBuffer },
        },
      ],
    });
    
    // 7. 創建 depth texture
    this.createDepthTexture();
    
    // 8. 創建 quad geometry（用於 instanced particle rendering）
    this.initQuadGeometry();
    
    // 9. 創建 boundary box pipeline
    this.initBoundaryBox();
    
    // 10. 創建 velocity trail pipeline
    if (this.enableTrails) {
      this.initTrails();
    }
    
    // 11. 創建 velocity vector pipeline
    if (this.enableVelocityVectors) {
      this.initVelocityVectors();
    }
    
    // 12. 創建 resource sphere pipeline
    if (this.enableResources) {
      this.initResources();
    }
    
    // 13. 創建 group boundary sphere pipeline
    if (this.enableGroupBoundaries) {
      this.initGroupBoundaries();
    }
    
    console.log('✅ WebGPU initialized successfully');
  }
  
  /**
   * 創建或重建 particle render pipeline
   * （支援動態切換 colorMode）
   */
  private createRenderPipeline(): void {
    const format = navigator.gpu.getPreferredCanvasFormat();
    
    // 創建 shader module（根據當前 colorMode）
    const shaderModule = this.device.createShaderModule({
      label: 'Particle Shader',
      code: this.getShaderCode(),
    });
    
    // Bind group layout
    const uniformBindGroupLayout = this.device.createBindGroupLayout({
      label: 'Uniform Bind Group Layout',
      entries: [
        {
          binding: 0,
          visibility: GPUShaderStage.VERTEX,
          buffer: { type: 'uniform' },
        },
      ],
    });
    
    // Pipeline layout
    const pipelineLayout = this.device.createPipelineLayout({
      label: 'Particle Pipeline Layout',
      bindGroupLayouts: [uniformBindGroupLayout],
    });
    
    // Vertex buffer layouts（根據 colorMode 動態調整）
    const bufferLayouts: GPUVertexBufferLayout[] = [
      // Buffer 0: quad vertices (shared, vec2f)
      {
        arrayStride: 8, // 2 * float32
        attributes: [
          {
            shaderLocation: 0,
            offset: 0,
            format: 'float32x2',
          },
        ],
      },
      // Buffer 1: particle positions (instanced, vec3f)
      {
        arrayStride: 12, // 3 * float32
        stepMode: 'instance',
        attributes: [
          {
            shaderLocation: 1,
            offset: 0,
            format: 'float32x3',
          },
        ],
      },
      // Buffer 2: particle types (instanced, uint32)
      {
        arrayStride: 4, // uint32
        stepMode: 'instance',
        attributes: [
          {
            shaderLocation: 2,
            offset: 0,
            format: 'uint32',
          },
        ],
      },
    ];
    
    // Buffer 3: group labels (conditional)
    if (this.colorMode === 'group') {
      bufferLayouts.push({
        arrayStride: 4, // uint32
        stepMode: 'instance',
        attributes: [
          {
            shaderLocation: 3,
            offset: 0,
            format: 'uint32',
          },
        ],
      });
    }
    
    this.pipeline = this.device.createRenderPipeline({
      label: 'Particle Pipeline',
      layout: pipelineLayout,
      vertex: {
        module: shaderModule,
        entryPoint: 'vs_main',
        buffers: bufferLayouts,
      },
      fragment: {
        module: shaderModule,
        entryPoint: 'fs_main',
        targets: [
          {
            format,
            blend: {
              color: {
                srcFactor: 'src-alpha',
                dstFactor: 'one-minus-src-alpha',
                operation: 'add',
              },
              alpha: {
                srcFactor: 'one',
                dstFactor: 'one-minus-src-alpha',
                operation: 'add',
              },
            },
          },
        ],
      },
      primitive: {
        topology: 'triangle-list', // 使用三角形渲染 quad
      },
      depthStencil: {
        format: 'depth24plus',
        depthWriteEnabled: true,
        depthCompare: 'less',
      },
    });
  }
  
  /**
   * 初始化 Quad 幾何（用於 particle instancing）
   */
  private initQuadGeometry(): void {
    // 創建一個 quad（2 個三角形，6 個頂點）
    // 座標範圍 [-1, 1]，後續在 shader 中縮放
    const vertices = new Float32Array([
      // Triangle 1
      -1, -1,  // Bottom-left
       1, -1,  // Bottom-right
      -1,  1,  // Top-left
      
      // Triangle 2
      -1,  1,  // Top-left
       1, -1,  // Bottom-right
       1,  1,  // Top-right
    ]);
    
    this.quadVertexBuffer = this.device.createBuffer({
      label: 'Quad Vertex Buffer',
      size: vertices.byteLength,
      usage: GPUBufferUsage.VERTEX,
      mappedAtCreation: true,
    });
    new Float32Array(this.quadVertexBuffer.getMappedRange()).set(vertices);
    this.quadVertexBuffer.unmap();
    
    console.log('✅ Quad geometry initialized');
  }
  
  /**
   * 初始化 Boundary Box 線框
   */
  private initBoundaryBox(): void {
    // 創建 box shader
    const boxShader = this.device.createShaderModule({
      label: 'Box Shader',
      code: this.getBoxShaderCode(),
    });
    
    // 創建 box pipeline (line-list)
    this.boxPipeline = this.device.createRenderPipeline({
      label: 'Box Pipeline',
      layout: this.device.createPipelineLayout({
        bindGroupLayouts: [this.device.createBindGroupLayout({
          entries: [
            {
              binding: 0,
              visibility: GPUShaderStage.VERTEX,
              buffer: { type: 'uniform' },
            },
          ],
        })],
      }),
      vertex: {
        module: boxShader,
        entryPoint: 'vs_main',
        buffers: [
          {
            arrayStride: 12, // vec3f
            attributes: [
              {
                shaderLocation: 0,
                offset: 0,
                format: 'float32x3',
              },
            ],
          },
        ],
      },
      fragment: {
        module: boxShader,
        entryPoint: 'fs_main',
        targets: [
          {
            format: navigator.gpu.getPreferredCanvasFormat(),
          },
        ],
      },
      primitive: {
        topology: 'line-list',
      },
      depthStencil: {
        format: 'depth24plus',
        depthWriteEnabled: true,
        depthCompare: 'less',
      },
    });
    
    // 創建 box 頂點（12 條邊 = 24 個頂點）
    this.updateBoundaryBox(this.boxSize);
  }
  
  /**
   * 更新 boundary box 大小
   */
  updateBoundaryBox(size: number): void {
    this.boxSize = size;
    const half = size / 2;
    
    // 12 條邊（每條邊 2 個頂點）
    const vertices = new Float32Array([
      // Bottom square
      -half, -half, -half,  half, -half, -half,
       half, -half, -half,  half, -half,  half,
       half, -half,  half, -half, -half,  half,
      -half, -half,  half, -half, -half, -half,
      
      // Top square
      -half,  half, -half,  half,  half, -half,
       half,  half, -half,  half,  half,  half,
       half,  half,  half, -half,  half,  half,
      -half,  half,  half, -half,  half, -half,
      
      // Vertical edges
      -half, -half, -half, -half,  half, -half,
       half, -half, -half,  half,  half, -half,
       half, -half,  half,  half,  half,  half,
      -half, -half,  half, -half,  half,  half,
    ]);
    
    // 創建或更新 buffer
    if (this.boxBuffer) {
      this.boxBuffer.destroy();
    }
    
    this.boxBuffer = this.device.createBuffer({
      label: 'Box Vertex Buffer',
      size: vertices.byteLength,
      usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
    });
    
    this.device.queue.writeBuffer(this.boxBuffer, 0, vertices);
  }
  
  /**
   * 生成 icosphere 幾何（基於正二十面體）
   * @param radius 球體半徑
   * @returns 包含頂點與索引的物件
   */
  private generateIcosphereGeometry(radius: number = 1.0): {
    vertices: Float32Array;
    indices: Uint16Array;
  } {
    // 黃金比例
    const phi = (1 + Math.sqrt(5)) / 2;
    const a = 1.0;
    const b = 1.0 / phi;
    
    // 標準化到指定半徑
    const len = Math.sqrt(a * a + b * b);
    const scale = radius / len;
    
    // 正二十面體的 12 個頂點（每個頂點包含 position 與 normal）
    // Format: [x, y, z, nx, ny, nz, ...]
    const vertices = new Float32Array([
      // Vertex 0
      -b*scale,  a*scale,  0,       -b/len,  a/len,  0,
      // Vertex 1
       b*scale,  a*scale,  0,        b/len,  a/len,  0,
      // Vertex 2
      -b*scale, -a*scale,  0,       -b/len, -a/len,  0,
      // Vertex 3
       b*scale, -a*scale,  0,        b/len, -a/len,  0,
      // Vertex 4
       0,       -b*scale,  a*scale,  0,     -b/len,  a/len,
      // Vertex 5
       0,        b*scale,  a*scale,  0,      b/len,  a/len,
      // Vertex 6
       0,       -b*scale, -a*scale,  0,     -b/len, -a/len,
      // Vertex 7
       0,        b*scale, -a*scale,  0,      b/len, -a/len,
      // Vertex 8
       a*scale,  0,       -b*scale,  a/len,  0,     -b/len,
      // Vertex 9
       a*scale,  0,        b*scale,  a/len,  0,      b/len,
      // Vertex 10
      -a*scale,  0,       -b*scale, -a/len,  0,     -b/len,
      // Vertex 11
      -a*scale,  0,        b*scale, -a/len,  0,      b/len,
    ]);
    
    // 正二十面體的 20 個三角形（60 個索引）
    const indices = new Uint16Array([
      // 5 faces around point 0
      0, 11, 5,
      0, 5, 1,
      0, 1, 7,
      0, 7, 10,
      0, 10, 11,
      
      // 5 adjacent faces
      1, 5, 9,
      5, 11, 4,
      11, 10, 2,
      10, 7, 6,
      7, 1, 8,
      
      // 5 faces around point 3
      3, 9, 4,
      3, 4, 2,
      3, 2, 6,
      3, 6, 8,
      3, 8, 9,
      
      // 5 adjacent faces
      4, 9, 5,
      2, 4, 11,
      6, 2, 10,
      8, 6, 7,
      9, 8, 1,
    ]);
    
    return { vertices, indices };
  }
  
  /**
   * 初始化 Velocity Trails
   */
  private initTrails(): void {
    // 創建 trail shader
    const trailShader = this.device.createShaderModule({
      label: 'Trail Shader',
      code: this.getTrailShaderCode(),
    });
    
    // 創建 trail pipeline (line-strip)
    this.trailPipeline = this.device.createRenderPipeline({
      label: 'Trail Pipeline',
      layout: this.device.createPipelineLayout({
        bindGroupLayouts: [this.device.createBindGroupLayout({
          entries: [
            {
              binding: 0,
              visibility: GPUShaderStage.VERTEX,
              buffer: { type: 'uniform' },
            },
          ],
        })],
      }),
      vertex: {
        module: trailShader,
        entryPoint: 'vs_main',
        buffers: [
          {
            arrayStride: 16, // vec3f position + float age
            attributes: [
              {
                shaderLocation: 0,
                offset: 0,
                format: 'float32x3',
              },
              {
                shaderLocation: 1,
                offset: 12,
                format: 'float32',
              },
            ],
          },
        ],
      },
      fragment: {
        module: trailShader,
        entryPoint: 'fs_main',
        targets: [
          {
            format: navigator.gpu.getPreferredCanvasFormat(),
            blend: {
              color: {
                srcFactor: 'src-alpha',
                dstFactor: 'one-minus-src-alpha',
                operation: 'add',
              },
              alpha: {
                srcFactor: 'one',
                dstFactor: 'one-minus-src-alpha',
                operation: 'add',
              },
            },
          },
        ],
      },
      primitive: {
        topology: 'line-strip',
        stripIndexFormat: 'uint32',
      },
      depthStencil: {
        format: 'depth24plus',
        depthWriteEnabled: true,
        depthCompare: 'less',
      },
    });
    
    console.log('✅ Trail pipeline initialized');
  }
  
  /**
   * 初始化速度向量渲染（箭頭）
   */
  private initVelocityVectors(): void {
    // 創建速度向量 shader
    const vectorShader = this.device.createShaderModule({
      label: 'Velocity Vector Shader',
      code: this.getVelocityVectorShaderCode(),
    });
    
    // 創建 velocity vector pipeline（line-list）
    this.velocityVectorPipeline = this.device.createRenderPipeline({
      label: 'Velocity Vector Pipeline',
      layout: this.device.createPipelineLayout({
        bindGroupLayouts: [this.device.createBindGroupLayout({
          entries: [
            {
              binding: 0,
              visibility: GPUShaderStage.VERTEX,
              buffer: { type: 'uniform' },
            },
          ],
        })],
      }),
      vertex: {
        module: vectorShader,
        entryPoint: 'vs_main',
        buffers: [
          {
            arrayStride: 12, // vec3f position
            attributes: [
              {
                shaderLocation: 0,
                offset: 0,
                format: 'float32x3',
              },
            ],
          },
        ],
      },
      fragment: {
        module: vectorShader,
        entryPoint: 'fs_main',
        targets: [
          {
            format: navigator.gpu.getPreferredCanvasFormat(),
            blend: {
              color: {
                srcFactor: 'src-alpha',
                dstFactor: 'one-minus-src-alpha',
                operation: 'add',
              },
              alpha: {
                srcFactor: 'one',
                dstFactor: 'one-minus-src-alpha',
                operation: 'add',
              },
            },
          },
        ],
      },
      primitive: {
        topology: 'line-list',
      },
      depthStencil: {
        format: 'depth24plus',
        depthWriteEnabled: false,
        depthCompare: 'less',
      },
    });
    
    console.log('✅ Velocity vector pipeline initialized');
  }
  
  /**
   * 初始化 Resource Spheres
   */
  private initResources(): void {
    // 生成球體幾何（半徑 1.0，後續透過 instance scale 調整）
    const sphere = this.generateIcosphereGeometry(1.0);
    this.sphereIndexCount = 60;
    
    // 創建頂點 buffer（position + normal）
    this.sphereVertexBuffer = this.device.createBuffer({
      label: 'Sphere Vertex Buffer',
      size: sphere.vertices.byteLength,
      usage: GPUBufferUsage.VERTEX,
      mappedAtCreation: true,
    });
    new Float32Array(this.sphereVertexBuffer.getMappedRange()).set(sphere.vertices);
    this.sphereVertexBuffer.unmap();
    
    // 創建索引 buffer
    this.sphereIndexBuffer = this.device.createBuffer({
      label: 'Sphere Index Buffer',
      size: sphere.indices.byteLength,
      usage: GPUBufferUsage.INDEX,
      mappedAtCreation: true,
    });
    new Uint16Array(this.sphereIndexBuffer.getMappedRange()).set(sphere.indices);
    this.sphereIndexBuffer.unmap();
    
    // 創建 resource shader
    const resourceShader = this.device.createShaderModule({
      label: 'Resource Shader',
      code: this.getResourceShaderCode(),
    });
    
    // 創建 resource pipeline（instanced rendering）
    this.resourcePipeline = this.device.createRenderPipeline({
      label: 'Resource Pipeline',
      layout: this.device.createPipelineLayout({
        bindGroupLayouts: [this.device.createBindGroupLayout({
          entries: [
            {
              binding: 0,
              visibility: GPUShaderStage.VERTEX,
              buffer: { type: 'uniform' },
            },
          ],
        })],
      }),
      vertex: {
        module: resourceShader,
        entryPoint: 'vs_main',
        buffers: [
          // Buffer 0: 球體幾何（position + normal）
          {
            arrayStride: 24, // 6 floats (vec3 position + vec3 normal)
            attributes: [
              {
                shaderLocation: 0,
                offset: 0,
                format: 'float32x3',
              },
              {
                shaderLocation: 1,
                offset: 12,
                format: 'float32x3',
              },
            ],
          },
          // Buffer 1: Instance 資料（position + scale + amount）
          {
            arrayStride: 20, // 5 floats (vec3 position + float scale + float amount)
            stepMode: 'instance',
            attributes: [
              {
                shaderLocation: 2,
                offset: 0,
                format: 'float32x3',
              },
              {
                shaderLocation: 3,
                offset: 12,
                format: 'float32',
              },
              {
                shaderLocation: 4,
                offset: 16,
                format: 'float32',
              },
            ],
          },
        ],
      },
      fragment: {
        module: resourceShader,
        entryPoint: 'fs_main',
        targets: [
          {
            format: navigator.gpu.getPreferredCanvasFormat(),
            blend: {
              color: {
                srcFactor: 'src-alpha',
                dstFactor: 'one-minus-src-alpha',
                operation: 'add',
              },
              alpha: {
                srcFactor: 'one',
                dstFactor: 'one-minus-src-alpha',
                operation: 'add',
              },
            },
          },
        ],
      },
      primitive: {
        topology: 'triangle-list',
        cullMode: 'back',
      },
      depthStencil: {
        format: 'depth24plus',
        depthWriteEnabled: true,
        depthCompare: 'less',
      },
    });
    
    console.log('✅ Resource pipeline initialized');
  }
  
  /**
   * 初始化 Group Boundary Spheres
   */
  private initGroupBoundaries(): void {
    // 球體幾何已經在 initResources() 中創建（共用 sphereVertexBuffer 和 sphereIndexBuffer）
    // 如果還沒創建，現在創建
    if (!this.sphereVertexBuffer || !this.sphereIndexBuffer) {
      const sphere = this.generateIcosphereGeometry(1.0);
      this.sphereIndexCount = 60;
      
      this.sphereVertexBuffer = this.device.createBuffer({
        label: 'Sphere Vertex Buffer',
        size: sphere.vertices.byteLength,
        usage: GPUBufferUsage.VERTEX,
        mappedAtCreation: true,
      });
      new Float32Array(this.sphereVertexBuffer.getMappedRange()).set(sphere.vertices);
      this.sphereVertexBuffer.unmap();
      
      this.sphereIndexBuffer = this.device.createBuffer({
        label: 'Sphere Index Buffer',
        size: sphere.indices.byteLength,
        usage: GPUBufferUsage.INDEX,
        mappedAtCreation: true,
      });
      new Uint16Array(this.sphereIndexBuffer.getMappedRange()).set(sphere.indices);
      this.sphereIndexBuffer.unmap();
    }
    
    // 創建 group sphere shader
    const groupSphereShader = this.device.createShaderModule({
      label: 'Group Sphere Shader',
      code: this.getGroupSphereShaderCode(),
    });
    
    // 創建 group sphere pipeline（instanced rendering）
    this.groupSpherePipeline = this.device.createRenderPipeline({
      label: 'Group Sphere Pipeline',
      layout: this.device.createPipelineLayout({
        bindGroupLayouts: [this.device.createBindGroupLayout({
          entries: [
            {
              binding: 0,
              visibility: GPUShaderStage.VERTEX,
              buffer: { type: 'uniform' },
            },
          ],
        })],
      }),
      vertex: {
        module: groupSphereShader,
        entryPoint: 'vs_main',
        buffers: [
          // Buffer 0: 球體幾何（position + normal）
          {
            arrayStride: 24, // 6 floats (vec3 position + vec3 normal)
            attributes: [
              {
                shaderLocation: 0,
                offset: 0,
                format: 'float32x3',
              },
              {
                shaderLocation: 1,
                offset: 12,
                format: 'float32x3',
              },
            ],
          },
          // Buffer 1: Instance 資料（centroid + radius + groupId + isSelected）
          {
            arrayStride: 24, // 6 floats (vec3 centroid + float radius + uint32 groupId + float isSelected)
            stepMode: 'instance',
            attributes: [
              {
                shaderLocation: 2,
                offset: 0,
                format: 'float32x3',
              },
              {
                shaderLocation: 3,
                offset: 12,
                format: 'float32',
              },
              {
                shaderLocation: 4,
                offset: 16,
                format: 'uint32',
              },
              {
                shaderLocation: 5,
                offset: 20,
                format: 'float32',
              },
            ],
          },
        ],
      },
      fragment: {
        module: groupSphereShader,
        entryPoint: 'fs_main',
        targets: [
          {
            format: navigator.gpu.getPreferredCanvasFormat(),
            blend: {
              color: {
                srcFactor: 'src-alpha',
                dstFactor: 'one-minus-src-alpha',
                operation: 'add',
              },
              alpha: {
                srcFactor: 'one',
                dstFactor: 'one-minus-src-alpha',
                operation: 'add',
              },
            },
          },
        ],
      },
      primitive: {
        topology: 'triangle-list',
        cullMode: 'back',
      },
      depthStencil: {
        format: 'depth24plus',
        depthWriteEnabled: false, // 不寫入 depth，讓粒子能顯示在前面
        depthCompare: 'less',
      },
    });
    
    console.log('✅ Group boundary pipeline initialized');
  }
  
  /**
   * 初始化群組速度箭頭渲染
   */
  private initGroupVelocityArrows(): void {
    if (!this.device) return;
    
    // 創建 shader
    const arrowShader = this.device.createShaderModule({
      label: 'Group Velocity Arrow Shader',
      code: this.getGroupVelocityArrowShaderCode(),
    });
    
    // 創建 pipeline (line-list)
    this.groupVelocityArrowPipeline = this.device.createRenderPipeline({
      label: 'Group Velocity Arrow Pipeline',
      layout: this.device.createPipelineLayout({
        bindGroupLayouts: [this.device.createBindGroupLayout({
          entries: [
            {
              binding: 0,
              visibility: GPUShaderStage.VERTEX,
              buffer: { type: 'uniform' },
            },
          ],
        })],
      }),
      vertex: {
        module: arrowShader,
        entryPoint: 'vs_main',
        buffers: [
          {
            arrayStride: 16, // vec3f position + u32 groupId
            attributes: [
              {
                shaderLocation: 0,
                offset: 0,
                format: 'float32x3',
              },
              {
                shaderLocation: 1,
                offset: 12,
                format: 'uint32',
              },
            ],
          },
        ],
      },
      fragment: {
        module: arrowShader,
        entryPoint: 'fs_main',
        targets: [
          {
            format: navigator.gpu.getPreferredCanvasFormat(),
            blend: {
              color: {
                srcFactor: 'src-alpha',
                dstFactor: 'one-minus-src-alpha',
                operation: 'add',
              },
              alpha: {
                srcFactor: 'one',
                dstFactor: 'one-minus-src-alpha',
                operation: 'add',
              },
            },
          },
        ],
      },
      primitive: {
        topology: 'line-list',
      },
      depthStencil: {
        format: 'depth24plus',
        depthWriteEnabled: false,
        depthCompare: 'less',
      },
    });
    
    console.log('✅ Group velocity arrow pipeline initialized');
  }
  
  /**
   * 更新歷史位置（Circular buffer）
   */
  private updatePositionHistory(positions: Float32Array): void {
    // 複製當前位置
    const currentPositions = new Float32Array(positions);
    
    // 加入 circular buffer
    if (this.positionHistory.length < this.trailLength) {
      this.positionHistory.push(currentPositions);
    } else {
      // 覆蓋最舊的
      this.positionHistory[this.currentHistoryIndex] = currentPositions;
      this.currentHistoryIndex = (this.currentHistoryIndex + 1) % this.trailLength;
    }
  }
  
  /**
   * 建立 trail buffer（每個粒子的軌跡）
   */
  private buildTrailBuffer(): void {
    if (this.positionHistory.length === 0 || this.particleCount === 0) return;
    
    const historyCount = this.positionHistory.length;
    
    // 每個粒子有 historyCount 個點，每個點 4 個 float (x, y, z, age)
    const verticesPerTrail = historyCount;
    const totalVertices = this.particleCount * verticesPerTrail;
    const data = new Float32Array(totalVertices * 4);
    
    // 填充資料
    for (let i = 0; i < this.particleCount; i++) {
      for (let t = 0; t < historyCount; t++) {
        // 計算實際歷史索引（從最舊到最新）
        const historyIdx = (this.currentHistoryIndex + t) % historyCount;
        const positions = this.positionHistory[historyIdx];
        
        // 基礎索引
        const baseIdx = (i * verticesPerTrail + t) * 4;
        
        // Position
        data[baseIdx + 0] = positions[i * 3 + 0];
        data[baseIdx + 1] = positions[i * 3 + 1];
        data[baseIdx + 2] = positions[i * 3 + 2];
        
        // Age (0 = oldest, 1 = newest)
        data[baseIdx + 3] = t / (historyCount - 1);
      }
    }
    
    // 創建或更新 buffer
    const bufferSize = data.byteLength;
    
    if (!this.trailBuffer || this.trailBuffer.size !== bufferSize) {
      if (this.trailBuffer) {
        this.trailBuffer.destroy();
      }
      
      this.trailBuffer = this.device.createBuffer({
        label: 'Trail Buffer',
        size: bufferSize,
        usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
      });
    }
    
    this.device.queue.writeBuffer(this.trailBuffer, 0, data);

    // 建立 primitive restart index buffer
    // 每條軌跡：historyCount 個索引 + 1 個哨兵值 0xFFFFFFFF
    const indexCount = this.particleCount * (historyCount + 1);
    const indexData = new Uint32Array(indexCount);
    for (let i = 0; i < this.particleCount; i++) {
      const base = i * (historyCount + 1);
      const vertexBase = i * historyCount;
      for (let t = 0; t < historyCount; t++) {
        indexData[base + t] = vertexBase + t;
      }
      indexData[base + historyCount] = 0xFFFFFFFF; // primitive restart sentinel
    }

    const indexBufferSize = indexData.byteLength;
    if (!this.trailIndexBuffer || this.trailIndexBuffer.size !== indexBufferSize) {
      if (this.trailIndexBuffer) this.trailIndexBuffer.destroy();
      this.trailIndexBuffer = this.device.createBuffer({
        label: 'Trail Index Buffer',
        size: indexBufferSize,
        usage: GPUBufferUsage.INDEX | GPUBufferUsage.COPY_DST,
      });
    }
    this.device.queue.writeBuffer(this.trailIndexBuffer, 0, indexData);
  }

  /**
   * 構建速度向量 buffer（箭頭）
   */
  private buildVelocityVectorBuffer(): void {
    if (!this.velocityData || this.particleCount === 0) return;
    
    const positions = this.positionHistory[this.positionHistory.length - 1] || new Float32Array();
    if (positions.length === 0) return;
    
    // 每個粒子2個頂點（起點和終點），每個頂點3個float
    const data = new Float32Array(this.particleCount * 2 * 3);
    const scale = 3.0; // 速度向量的縮放係數，讓它可見
    
    for (let i = 0; i < this.particleCount; i++) {
      const px = positions[i * 3 + 0];
      const py = positions[i * 3 + 1];
      const pz = positions[i * 3 + 2];
      
      const vx = this.velocityData[i * 3 + 0];
      const vy = this.velocityData[i * 3 + 1];
      const vz = this.velocityData[i * 3 + 2];
      
      // 起點（粒子位置）
      data[i * 6 + 0] = px;
      data[i * 6 + 1] = py;
      data[i * 6 + 2] = pz;
      
      // 終點（粒子位置 + 速度 × 縮放）
      data[i * 6 + 3] = px + vx * scale;
      data[i * 6 + 4] = py + vy * scale;
      data[i * 6 + 5] = pz + vz * scale;
    }
    
    // 創建或更新 buffer
    const bufferSize = data.byteLength;
    
    if (!this.velocityVectorBuffer || this.velocityVectorBuffer.size !== bufferSize) {
      if (this.velocityVectorBuffer) {
        this.velocityVectorBuffer.destroy();
      }
      
      this.velocityVectorBuffer = this.device.createBuffer({
        label: 'Velocity Vector Buffer',
        size: bufferSize,
        usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
      });
    }
    
    this.device.queue.writeBuffer(this.velocityVectorBuffer, 0, data);
  }
  
  /**
   * 構建群組速度箭頭 buffer
   */
  private buildGroupVelocityArrowBuffer(): void {
    if (this.groupVelocityData.length === 0) return;
    
    const arrowScale = 5.0; // 箭頭長度縮放係數
    
    // 每個群組 2 個頂點（起點和終點），每個頂點 4 個值 (x, y, z, groupId)
    const data = new Float32Array(this.groupVelocityData.length * 2 * 4);
    
    for (let i = 0; i < this.groupVelocityData.length; i++) {
      const group = this.groupVelocityData[i];
      const [cx, cy, cz] = group.centroid;
      const [vx, vy, vz] = group.velocity;
      
      // 起點（群組質心）
      const startIdx = i * 8;
      data[startIdx + 0] = cx;
      data[startIdx + 1] = cy;
      data[startIdx + 2] = cz;
      const groupIdView = new Uint32Array(data.buffer, (startIdx + 3) * 4, 1);
      groupIdView[0] = group.groupId;
      
      // 終點（質心 + 速度 × 縮放）
      const endIdx = i * 8 + 4;
      data[endIdx + 0] = cx + vx * arrowScale;
      data[endIdx + 1] = cy + vy * arrowScale;
      data[endIdx + 2] = cz + vz * arrowScale;
      const groupIdView2 = new Uint32Array(data.buffer, (endIdx + 3) * 4, 1);
      groupIdView2[0] = group.groupId;
    }
    
    // 創建或更新 buffer
    const bufferSize = data.byteLength;
    
    if (!this.groupVelocityArrowBuffer || this.groupVelocityArrowBuffer.size !== bufferSize) {
      if (this.groupVelocityArrowBuffer) {
        this.groupVelocityArrowBuffer.destroy();
      }
      
      this.groupVelocityArrowBuffer = this.device.createBuffer({
        label: 'Group Velocity Arrow Buffer',
        size: bufferSize,
        usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
      });
    }
    
    this.device.queue.writeBuffer(this.groupVelocityArrowBuffer, 0, data);
  }
  
  /**
   * 更新群組邊界球體的 instance buffer
   */
  private updateResourceBuffer(resources: Array<{
    position: [number, number, number];
    amount: number;
    radius: number;
    renewable: boolean;
  }>): void {
    if (resources.length === 0) {
      this.resourceCount = 0;
      return;
    }
    
    this.resourceCount = resources.length;
    
    // 準備 instance 資料: [x, y, z, scale, amount]
    const instanceData = new Float32Array(this.resourceCount * 5);
    
    for (let i = 0; i < this.resourceCount; i++) {
      const res = resources[i];
      const baseIdx = i * 5;
      
      instanceData[baseIdx + 0] = res.position[0];
      instanceData[baseIdx + 1] = res.position[1];
      instanceData[baseIdx + 2] = res.position[2];
      instanceData[baseIdx + 3] = res.radius;
      instanceData[baseIdx + 4] = res.amount; // 在 shader 中標準化
    }
    
    // 創建或更新 buffer
    const bufferSize = instanceData.byteLength;
    
    if (!this.resourceInstanceBuffer || this.resourceInstanceBuffer.size !== bufferSize) {
      if (this.resourceInstanceBuffer) {
        this.resourceInstanceBuffer.destroy();
      }
      
      this.resourceInstanceBuffer = this.device.createBuffer({
        label: 'Resource Instance Buffer',
        size: bufferSize,
        usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
      });
    }
    
    this.device.queue.writeBuffer(this.resourceInstanceBuffer, 0, instanceData);
  }
  
  /**
   * 更新 group boundary instance buffer
   */
  private updateGroupBoundaryBuffer(groups: Array<{
    groupId: number;
    size: number;
    centroid: [number, number, number];
    velocity: [number, number, number];
    radius: number;
  }>): void {
    if (groups.length === 0) {
      this.groupCount = 0;
      return;
    }
    
    // 顯示所有有效群組（size > 0），避免邊界/箭頭因門檻過高而完全不顯示
    const validGroups = groups.filter(g => g.size > 0);
    
    if (validGroups.length === 0) {
      this.groupCount = 0;
      return;
    }
    
    this.groupCount = validGroups.length;
    
    // 準備 instance 資料: [x, y, z, radius, groupId, isSelected]
    // 每個實例 6 個 float（最後一個用 0/1 表示是否選中）
    const instanceData = new Float32Array(this.groupCount * 6);
    
    for (let i = 0; i < this.groupCount; i++) {
      const group = validGroups[i];
      const baseIdx = i * 6;
      
      instanceData[baseIdx + 0] = group.centroid[0];
      instanceData[baseIdx + 1] = group.centroid[1];
      instanceData[baseIdx + 2] = group.centroid[2];
      instanceData[baseIdx + 3] = group.radius;
      
      // 將 groupId 轉換為 float32（在 shader 中會轉回 uint32）
      const view = new DataView(instanceData.buffer);
      view.setUint32((baseIdx + 4) * 4, group.groupId, true);
      
      // isSelected (0.0 或 1.0)
      instanceData[baseIdx + 5] = (this.selectedGroupId === group.groupId) ? 1.0 : 0.0;
    }
    
    // 創建或更新 buffer
    const bufferSize = instanceData.byteLength;
    
    if (!this.groupSphereInstanceBuffer || this.groupSphereInstanceBuffer.size !== bufferSize) {
      if (this.groupSphereInstanceBuffer) {
        this.groupSphereInstanceBuffer.destroy();
      }
      
      this.groupSphereInstanceBuffer = this.device.createBuffer({
        label: 'Group Sphere Instance Buffer',
        size: bufferSize,
        usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
      });
    }
    
    this.device.queue.writeBuffer(this.groupSphereInstanceBuffer, 0, instanceData);
  }
  
  /**
   * 創建 depth texture（只在 init/resize 時呼叫）
   */
  private createDepthTexture(): void {
    if (!this.canvas) return;
    
    // 銷毀舊的 texture
    if (this.depthTexture) {
      this.depthTexture.destroy();
    }
    
    this.depthTexture = this.device.createTexture({
      size: {
        width: this.canvas.width,
        height: this.canvas.height,
      },
      format: 'depth24plus',
      usage: GPUTextureUsage.RENDER_ATTACHMENT,
    });
    
    this.depthTextureView = this.depthTexture.createView();
  }
  
  /**
   * Resize depth texture（當 canvas 大小改變時呼叫）
   */
  resize(width: number, height: number): void {
    if (!this.canvas) return;
    this.canvas.width = width;
    this.canvas.height = height;
    this.createDepthTexture();
  }
  
  /**
   * 上傳粒子資料到 GPU
   */
  updateParticles(data: RenderData): void {
    const { positions, velocities, types, groupLabels, boxSize, resources, groups } = data;
    const N = positions.length / 3;
    
    console.log(`🔄 updateParticles called: N=${N}, positions.length=${positions.length}`);
    
    if (N === 0) return;
    
    // 保存速度資料（用於速度向量渲染）
    if (velocities && this.enableVelocityVectors) {
      this.velocityData = velocities;
    }
    
    // 更新 box size（如果提供）
    if (boxSize && boxSize !== this.boxSize) {
      this.updateBoundaryBox(boxSize);
    }
    
    // 更新 resources（如果提供）
    if (this.enableResources && resources) {
      this.updateResourceBuffer(resources);
    }
    
    // 更新 group boundaries（如果提供）
    if (this.enableGroupBoundaries && groups) {
      this.updateGroupBoundaryBuffer(groups);
    }
    
    // 更新 group velocity arrows（如果提供且啟用）
    if (this.enableGroupVelocityArrows && groups) {
      // 過濾有效群組並提取速度資料
      this.groupVelocityData = groups
        .filter(g => g.size > 0)
        .map(g => ({
          centroid: g.centroid,
          velocity: g.velocity,
          groupId: g.groupId,
        }));
    }
    
    // 更新歷史位置（用於 trails）
    if (this.enableTrails) {
      this.updatePositionHistory(positions);
    }
    
    // 1. 創建或更新 position buffer
    if (!this.positionBuffer || this.particleCount !== N) {
      if (this.positionBuffer) {
        this.positionBuffer.destroy();
      }
      this.positionBuffer = this.device.createBuffer({
        label: 'Position Buffer',
        size: positions.byteLength,
        usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
      });
    }
    this.device.queue.writeBuffer(this.positionBuffer, 0, positions.buffer);
    
    // 2. 創建或更新 type buffer (需要轉換為 uint32)
    const typesU32 = new Uint32Array(N);
    for (let i = 0; i < N; i++) {
      typesU32[i] = types[i];
    }
    
    // Debug: 檢查掠食者 (type=3)
    const predatorIndices = Array.from(typesU32).map((t, i) => t === 3 ? i : -1).filter(i => i !== -1);
    if (predatorIndices.length > 0) {
      console.log(`🦁 Found ${predatorIndices.length} predators at indices:`, predatorIndices);
      console.log('Predator positions:', predatorIndices.map(i => [positions[i*3], positions[i*3+1], positions[i*3+2]]));
    }
    
    if (!this.typeBuffer || this.particleCount !== N) {
      if (this.typeBuffer) {
        this.typeBuffer.destroy();
      }
      this.typeBuffer = this.device.createBuffer({
        label: 'Type Buffer',
        size: typesU32.byteLength,
        usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
      });
    }
    this.device.queue.writeBuffer(this.typeBuffer, 0, typesU32);
    
    // 3. 創建或更新 group label buffer (NEW)
    if (groupLabels) {
      const groupLabelsU32 = new Uint32Array(N);
      for (let i = 0; i < N; i++) {
        groupLabelsU32[i] = groupLabels[i];
      }
      
      if (!this.groupLabelBuffer || this.particleCount !== N) {
        if (this.groupLabelBuffer) {
          this.groupLabelBuffer.destroy();
        }
        this.groupLabelBuffer = this.device.createBuffer({
          label: 'Group Label Buffer',
          size: groupLabelsU32.byteLength,
          usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST,
        });
      }
      this.device.queue.writeBuffer(this.groupLabelBuffer, 0, groupLabelsU32);
    }
    
    this.particleCount = N;
    console.log(`✅ updateParticles complete: particleCount=${this.particleCount}`);
  }
  
  /**
   * 渲染一幀
   * @param viewMatrix 視圖矩陣 (from camera)
   * @param projMatrix 投影矩陣 (from camera)
   */
  render(viewMatrix: mat4, projMatrix: mat4): void {
    if (!this.canvas) return;
    
    // 1. 更新 uniform buffer (view + projection)
    const uniformData = new Float32Array(32); // 2 * 16 floats
    uniformData.set(viewMatrix, 0);
    uniformData.set(projMatrix, 16);
    this.device.queue.writeBuffer(this.uniformBuffer, 0, uniformData);
    
    // 2. 建立 trail buffer（如果啟用）
    if (this.enableTrails && this.positionHistory.length > 1) {
      this.buildTrailBuffer();
    }
    
    // 3. 開始 render pass
    const commandEncoder = this.device.createCommandEncoder();
    const textureView = this.context.getCurrentTexture().createView();
    
    const renderPass = commandEncoder.beginRenderPass({
      colorAttachments: [
        {
          view: textureView,
          clearValue: { r: 0.05, g: 0.05, b: 0.05, a: 1.0 }, // 深灰背景
          loadOp: 'clear',
          storeOp: 'store',
        },
      ],
      depthStencilAttachment: {
        view: this.depthTextureView,
        depthClearValue: 1.0,
        depthLoadOp: 'clear',
        depthStoreOp: 'store',
      },
    });
    
    // 4. 繪製 boundary box（總是顯示）
    renderPass.setPipeline(this.boxPipeline);
    renderPass.setBindGroup(0, this.bindGroup);
    renderPass.setVertexBuffer(0, this.boxBuffer);
    renderPass.draw(24); // 12 edges * 2 vertices
    
    // 5. 繪製 velocity trails（在粒子之前，作為背景）
    if (this.enableTrails && this.trailBuffer && this.positionHistory.length > 1) {
      const historyCount = this.positionHistory.length;
      
      // DEBUG: Log trail rendering
      if (Math.random() < 0.016) {
        console.log(`🎨 Drawing trails: historyCount=${historyCount}, particleCount=${this.particleCount}`);
      }
      
      renderPass.setPipeline(this.trailPipeline);
      renderPass.setBindGroup(0, this.bindGroup);
      renderPass.setVertexBuffer(0, this.trailBuffer);
      
      // 每個粒子繪製一條 line-strip
      for (let i = 0; i < this.particleCount; i++) {
        const firstVertex = i * historyCount;
        renderPass.draw(historyCount, 1, firstVertex, 0);
      }
    } else if (Math.random() < 0.016) {
      console.log(`⚠️ Trails skipped: enableTrails=${this.enableTrails}, trailBuffer=${!!this.trailBuffer}, historyCount=${this.positionHistory.length}`);
    }
    
    // 6. 繪製 resources（在粒子之前，作為半透明物體）
    if (this.enableResources && this.resourceCount > 0 && this.resourceInstanceBuffer) {
      renderPass.setPipeline(this.resourcePipeline);
      renderPass.setBindGroup(0, this.bindGroup);
      renderPass.setVertexBuffer(0, this.sphereVertexBuffer);
      renderPass.setVertexBuffer(1, this.resourceInstanceBuffer);
      renderPass.setIndexBuffer(this.sphereIndexBuffer, 'uint16');
      renderPass.drawIndexed(this.sphereIndexCount, this.resourceCount, 0, 0, 0);
    }
    
    // 6.5. 繪製 group boundaries（在粒子之前，作為半透明邊界）
    if (this.enableGroupBoundaries && this.groupCount > 0 && this.groupSphereInstanceBuffer && this.groupSpherePipeline) {
      // 防禦性檢查：確保所有必要的資源都存在
      if (!this.sphereVertexBuffer || !this.sphereIndexBuffer) {
        console.warn('⚠️ Group boundaries enabled but sphere buffers not initialized');
      } else if (!this.bindGroup) {
        console.warn('⚠️ Group boundaries enabled but bind group not initialized');
      } else {
        try {
          renderPass.setPipeline(this.groupSpherePipeline);
          renderPass.setBindGroup(0, this.bindGroup);
          renderPass.setVertexBuffer(0, this.sphereVertexBuffer);
          renderPass.setVertexBuffer(1, this.groupSphereInstanceBuffer);
          renderPass.setIndexBuffer(this.sphereIndexBuffer, 'uint16');
          renderPass.drawIndexed(this.sphereIndexCount, this.groupCount, 0, 0, 0);
          
          if (Math.random() < 0.016) {
            console.log(`🔮 Drawing ${this.groupCount} group boundaries`);
          }
        } catch (error) {
          console.error('❌ Error drawing group boundaries:', error);
          this.enableGroupBoundaries = false; // 關閉以避免持續錯誤
        }
      }
    }
    
    // 7. 繪製粒子（instanced quads）
    if (this.particleCount > 0) {
      renderPass.setPipeline(this.pipeline);
      renderPass.setBindGroup(0, this.bindGroup);
      renderPass.setVertexBuffer(0, this.quadVertexBuffer);  // Quad geometry
      renderPass.setVertexBuffer(1, this.positionBuffer);    // Particle positions (instanced)
      renderPass.setVertexBuffer(2, this.typeBuffer);        // Particle types (instanced)
      if (this.colorMode === 'group' && this.groupLabelBuffer) {
        renderPass.setVertexBuffer(3, this.groupLabelBuffer); // Group labels (instanced, conditional)
      }
      renderPass.draw(6, this.particleCount, 0, 0);          // 6 vertices per quad, N instances
      
      // DEBUG: Log once per second
      if (Math.random() < 0.016) {  // ~1/60 chance
        console.log(`🎨 Drawing ${this.particleCount} particles (6 vertices × ${this.particleCount} instances = ${6 * this.particleCount} total)`);
      }
    } else {
      if (Math.random() < 0.016) {
        console.log('⚠️ No particles to draw (particleCount = 0)');
      }
    }
    
    // 8. 繪製速度向量（在粒子之後，作為疊加層）
    if (this.enableVelocityVectors && this.velocityData && this.particleCount > 0) {
      this.buildVelocityVectorBuffer();
      if (this.velocityVectorBuffer) {
        renderPass.setPipeline(this.velocityVectorPipeline);
        renderPass.setBindGroup(0, this.bindGroup);
        renderPass.setVertexBuffer(0, this.velocityVectorBuffer);
        renderPass.draw(this.particleCount * 2); // 每個粒子2個頂點（起點和終點）
        
        if (Math.random() < 0.016) {
          console.log(`🎨 Drawing ${this.particleCount} velocity vectors`);
        }
      }
    }
    
    // 8.5. 繪製群組速度箭頭（在速度向量之後）
    if (this.enableGroupVelocityArrows && this.groupVelocityData.length > 0 && this.groupVelocityArrowPipeline) {
      this.buildGroupVelocityArrowBuffer();
      if (this.groupVelocityArrowBuffer) {
        try {
          renderPass.setPipeline(this.groupVelocityArrowPipeline);
          renderPass.setBindGroup(0, this.bindGroup);
          renderPass.setVertexBuffer(0, this.groupVelocityArrowBuffer);
          renderPass.draw(this.groupVelocityData.length * 2); // 每個群組2個頂點
          
          if (Math.random() < 0.016) {
            console.log(`➡️ Drawing ${this.groupVelocityData.length} group velocity arrows`);
          }
        } catch (error) {
          console.error('❌ Error drawing group velocity arrows:', error);
          this.enableGroupVelocityArrows = false; // 關閉以避免持續錯誤
        }
      }
    }
    
    renderPass.end();
    
    // 9. 提交命令
    this.device.queue.submit([commandEncoder.finish()]);
  }
  
  /**
   * 清理資源
   */
  destroy(): void {
    if (this.quadVertexBuffer) this.quadVertexBuffer.destroy();
    if (this.positionBuffer) this.positionBuffer.destroy();
    if (this.typeBuffer) this.typeBuffer.destroy();
    if (this.groupLabelBuffer) this.groupLabelBuffer.destroy();
    if (this.uniformBuffer) this.uniformBuffer.destroy();
    if (this.depthTexture) this.depthTexture.destroy();
    if (this.boxBuffer) this.boxBuffer.destroy();
    if (this.trailBuffer) this.trailBuffer.destroy();
    if (this.trailIndexBuffer) this.trailIndexBuffer.destroy();
    if (this.sphereVertexBuffer) this.sphereVertexBuffer.destroy();
    if (this.sphereIndexBuffer) this.sphereIndexBuffer.destroy();
    if (this.resourceInstanceBuffer) this.resourceInstanceBuffer.destroy();
    if (this.groupSphereInstanceBuffer) this.groupSphereInstanceBuffer.destroy();
    if (this.device) this.device.destroy();
  }
  
  /**
   * 取得當前設定
   */
  getOptions(): RendererOptions {
    return {
      enableTrails: this.enableTrails,
      trailLength: this.trailLength,
      enableResources: this.enableResources,
      enableGroupBoundaries: this.enableGroupBoundaries,
    };
  }
  
  /**
   * 切換 trails 開關
   */
  setEnableTrails(enabled: boolean): void {
    this.enableTrails = enabled;
    if (!enabled) {
      // 清空歷史
      this.positionHistory = [];
      this.currentHistoryIndex = 0;
    }
  }
  
  /**
   * 設定 trail 長度
   */
  setTrailLength(length: number): void {
    this.trailLength = Math.max(2, Math.min(30, length)); // 限制 2-30 幀
    
    // 裁剪歷史（如果變短）
    if (this.positionHistory.length > this.trailLength) {
      this.positionHistory = this.positionHistory.slice(0, this.trailLength);
      this.currentHistoryIndex = 0;
    }
  }
  
  /**
   * 切換 resources 開關
   */
  setEnableResources(enabled: boolean): void {
    this.enableResources = enabled;
  }
  
  /**
   * 取得 resources 狀態
   */
  getEnableResources(): boolean {
    return this.enableResources;
  }
  
  /**
   * 設定粒子大小
   */
  setParticleSize(size: number): void {
    this.particleSize = Math.max(0.1, Math.min(5.0, size)); // Clamp between 0.1 and 5.0
    console.log(`🎨 Particle size set to: ${this.particleSize}`);
  }
  
  /**
   * 取得粒子大小
   */
  getParticleSize(): number {
    return this.particleSize;
  }
  
  /**
   * 設定著色模式（依類型 or 依群組）
   */
  setColorMode(mode: 'type' | 'group'): void {
    if (this.colorMode !== mode) {
      this.colorMode = mode;
      console.log(`🎨 Color mode set to: ${mode}`);
      // 需要重建 pipeline（shader 不同）
      this.createRenderPipeline();
    }
  }
  
  /**
   * 取得著色模式
   */
  getColorMode(): 'type' | 'group' {
    return this.colorMode;
  }
  
  /**
   * 設定群組邊界顯示開關
   */
  setEnableGroupBoundaries(enabled: boolean): void {
    // 如果要啟用但 pipeline 還沒初始化，先初始化
    if (enabled && !this.groupSpherePipeline) {
      console.log('🔮 Initializing group boundaries pipeline...');
      
      // 確保 device 和 bindGroup 已就緒
      if (!this.device || !this.bindGroup) {
        console.error('❌ Cannot initialize group boundaries: device or bindGroup not ready');
        return;
      }
      
      try {
        this.initGroupBoundaries();
        console.log('✅ Group boundaries pipeline initialized successfully');
      } catch (error) {
        console.error('❌ Failed to initialize group boundaries:', error);
        return;
      }
    }
    
    this.enableGroupBoundaries = enabled;
    console.log(`🔮 Group boundaries ${enabled ? 'enabled' : 'disabled'}`);
  }
  
  /**
   * 取得群組邊界顯示狀態
   */
  getEnableGroupBoundaries(): boolean {
    return this.enableGroupBoundaries;
  }
  
  /**
   * 設定選中的群組 ID（用於高亮）
   */
  setSelectedGroupId(groupId: number | null): void {
    if (this.selectedGroupId !== groupId) {
      this.selectedGroupId = groupId;
      console.log(`🎯 Selected group for highlighting: ${groupId}`);
      // 不需要重建 pipeline，buffer 會在下一次 updateParticles 時自動更新
    }
  }
  
  /**
   * 取得選中的群組 ID
   */
  getSelectedGroupId(): number | null {
    return this.selectedGroupId;
  }
  
  /**
   * 設定群組速度箭頭顯示開關
   */
  setEnableGroupVelocityArrows(enabled: boolean): void {
    // 如果要啟用但 pipeline 還沒初始化，先初始化
    if (enabled && !this.groupVelocityArrowPipeline) {
      console.log('➡️ Initializing group velocity arrows pipeline...');
      
      // 確保 device 和 bindGroup 已就緒
      if (!this.device || !this.bindGroup) {
        console.error('❌ Cannot initialize group velocity arrows: device or bindGroup not ready');
        return;
      }
      
      try {
        this.initGroupVelocityArrows();
        console.log('✅ Group velocity arrows pipeline initialized successfully');
      } catch (error) {
        console.error('❌ Failed to initialize group velocity arrows:', error);
        return;
      }
    }
    
    this.enableGroupVelocityArrows = enabled;
    console.log(`➡️ Group velocity arrows ${enabled ? 'enabled' : 'disabled'}`);
  }
  
  /**
   * 取得群組速度箭頭顯示狀態
   */
  getEnableGroupVelocityArrows(): boolean {
    return this.enableGroupVelocityArrows;
  }
  
  /**
   * WGSL Shader 代碼（Instanced Billboarded Quads）
   */
  private getShaderCode(): string {
    const useGroupColor = this.colorMode === 'group';
    
    return `
      // Uniforms (view + projection matrices)
      struct Uniforms {
        view: mat4x4f,
        projection: mat4x4f,
      };
      @group(0) @binding(0) var<uniform> uniforms: Uniforms;
      
      // Vertex input
      struct VertexInput {
        @location(0) quadPos: vec2f,     // Quad vertex position (-1 to 1)
        @location(1) particlePos: vec3f, // Particle world position (instanced)
        @location(2) agent_type: u32,    // Agent type (instanced)
        ${useGroupColor ? '@location(3) group_label: u32,    // Group ID (instanced)' : ''}
      };
      
      // Vertex output
      struct VertexOutput {
        @builtin(position) position: vec4f,
        @location(0) color: vec3f,
        @location(1) quadCoord: vec2f,  // For circular shape
      };
      
      // HSL to RGB conversion
      fn hsl_to_rgb(h: f32, s: f32, l: f32) -> vec3f {
        let c = (1.0 - abs(2.0 * l - 1.0)) * s;
        let x = c * (1.0 - abs((h * 6.0) % 2.0 - 1.0));
        let m = l - c / 2.0;
        
        var rgb = vec3f(0.0);
        let h6 = h * 6.0;
        if (h6 < 1.0) {
          rgb = vec3f(c, x, 0.0);
        } else if (h6 < 2.0) {
          rgb = vec3f(x, c, 0.0);
        } else if (h6 < 3.0) {
          rgb = vec3f(0.0, c, x);
        } else if (h6 < 4.0) {
          rgb = vec3f(0.0, x, c);
        } else if (h6 < 5.0) {
          rgb = vec3f(x, 0.0, c);
        } else {
          rgb = vec3f(c, 0.0, x);
        }
        
        return rgb + vec3f(m);
      }
      
      // Hash function for group_id -> color
      fn group_to_color(group_id: u32) -> vec3f {
        // Simple hash to get consistent color per group
        let seed = f32(group_id) * 0.618033988749895; // Golden ratio
        let hue = fract(seed);
        let saturation = 0.7;
        let lightness = 0.6;
        return hsl_to_rgb(hue, saturation, lightness);
      }
      
      // Vertex shader: Billboard quad rendering
      @vertex
      fn vs_main(in: VertexInput) -> VertexOutput {
        var out: VertexOutput;
        
        // Transform particle center to view space
        let worldPos = vec4f(in.particlePos, 1.0);
        let viewPos = uniforms.view * worldPos;
        
        // Billboard size (in world space units, not view space)
        // Predators (type=3) are 1.5x larger
        let baseSize = 0.5;  // Particle radius in world units (boxSize=50)
        let size = select(baseSize, baseSize * 1.5, in.agent_type == 3u);
        
        // Get camera right and up vectors from view matrix
        // (inverse of view matrix rotation)
        let right = vec3f(uniforms.view[0][0], uniforms.view[1][0], uniforms.view[2][0]);
        let up = vec3f(uniforms.view[0][1], uniforms.view[1][1], uniforms.view[2][1]);
        
        // Create billboard in world space
        let billboardOffset = right * in.quadPos.x * size + up * in.quadPos.y * size;
        let billboardWorldPos = in.particlePos + billboardOffset;
        
        // Transform to clip space
        let billboardViewPos = uniforms.view * vec4f(billboardWorldPos, 1.0);
        out.position = uniforms.projection * billboardViewPos;
        
        ${useGroupColor ? `
        // Group coloring mode
        if (in.group_label == 0xFFFFFFFFu || in.group_label == 4294967295u) {
          // Invalid group: use gray
          out.color = vec3f(0.5, 0.5, 0.5);
        } else {
          out.color = group_to_color(in.group_label);
        }
        ` : `
        // Agent type coloring mode
        // 0=Follower (Blue), 1=Explorer (Orange), 2=Leader (Pink), 3=Predator (White)
        let colors = array<vec3f, 4>(
          vec3f(0.39, 0.70, 0.93),  // #63b3ed - Blue (Follower)
          vec3f(0.96, 0.68, 0.33),  // #f6ad55 - Orange (Explorer)
          vec3f(0.99, 0.51, 0.51),  // #fc8181 - Pink (Leader)
          vec3f(1.0, 1.0, 1.0)      // #ffffff - White (Predator)
        );
        
        let typeIndex = min(in.agent_type, 3u);
        out.color = colors[typeIndex];
        `}
        
        // Pass quad coordinate for circular masking
        out.quadCoord = in.quadPos;
        
        return out;
      }
      
      // Fragment shader: Circular masking + soft edges
      @fragment
      fn fs_main(in: VertexOutput) -> @location(0) vec4f {
        // Calculate distance from center of quad
        let dist = length(in.quadCoord);
        
        // Discard pixels outside circle (makes particles round)
        if (dist > 1.0) {
          discard;
        }
        
        // Soft edge: fade alpha near edge for anti-aliasing
        let alpha = 1.0 - smoothstep(0.85, 1.0, dist);
        
        return vec4f(in.color, alpha);
      }
    `;
  }
  
  /**
   * WGSL Shader for Boundary Box
   */
  private getBoxShaderCode(): string {
    return `
      // Uniforms (view + projection matrices)
      struct Uniforms {
        view: mat4x4f,
        projection: mat4x4f,
      };
      @group(0) @binding(0) var<uniform> uniforms: Uniforms;
      
      // Vertex input
      struct VertexInput {
        @location(0) position: vec3f,
      };
      
      // Vertex output
      struct VertexOutput {
        @builtin(position) position: vec4f,
      };
      
      // Vertex shader: Transform lines
      @vertex
      fn vs_main(in: VertexInput) -> VertexOutput {
        var out: VertexOutput;
        
        let worldPos = vec4f(in.position, 1.0);
        let viewPos = uniforms.view * worldPos;
        out.position = uniforms.projection * viewPos;
        
        return out;
      }
      
      // Fragment shader: White lines with transparency
      @fragment
      fn fs_main(in: VertexOutput) -> @location(0) vec4f {
        return vec4f(0.5, 0.5, 0.5, 0.3);  // Semi-transparent gray
      }
    `;
  }
  
  /**
   * WGSL Shader for Velocity Trails
   */
  private getTrailShaderCode(): string {
    return `
      // Uniforms (view + projection matrices)
      struct Uniforms {
        view: mat4x4f,
        projection: mat4x4f,
      };
      @group(0) @binding(0) var<uniform> uniforms: Uniforms;
      
      // Vertex input
      struct VertexInput {
        @location(0) position: vec3f,
        @location(1) age: f32,  // 0 = oldest, 1 = newest
      };
      
      // Vertex output
      struct VertexOutput {
        @builtin(position) position: vec4f,
        @location(0) age: f32,
      };
      
      // Vertex shader: Transform trail points
      @vertex
      fn vs_main(in: VertexInput) -> VertexOutput {
        var out: VertexOutput;
        
        let worldPos = vec4f(in.position, 1.0);
        let viewPos = uniforms.view * worldPos;
        out.position = uniforms.projection * viewPos;
        out.age = in.age;
        
        return out;
      }
      
      // Fragment shader: Fade-out effect (older = more transparent)
      @fragment
      fn fs_main(in: VertexOutput) -> @location(0) vec4f {
        // Color: White with fade-out
        // age: 0 (oldest) → alpha = 0.0
        // age: 1 (newest) → alpha = 0.8
        let alpha = in.age * 0.8;
        
        // Soft white color
        return vec4f(0.9, 0.9, 0.9, alpha);
      }
    `;
  }
  
  /**
   * WGSL Shader for Resource Spheres
   */
  private getResourceShaderCode(): string {
    return `
      // Uniforms (view + projection matrices)
      struct Uniforms {
        view: mat4x4f,
        projection: mat4x4f,
      };
      @group(0) @binding(0) var<uniform> uniforms: Uniforms;
      
      // Vertex input (sphere geometry)
      struct VertexInput {
        @location(0) position: vec3f,
        @location(1) normal: vec3f,
      };
      
      // Instance input (resource data)
      struct InstanceInput {
        @location(2) instancePos: vec3f,
        @location(3) scale: f32,
        @location(4) amount: f32,  // 0-100
      };
      
      // Vertex output
      struct VertexOutput {
        @builtin(position) position: vec4f,
        @location(0) worldNormal: vec3f,
        @location(1) amount: f32,
      };
      
      // Vertex shader: Transform sphere with instancing
      @vertex
      fn vs_main(vertex: VertexInput, instance: InstanceInput) -> VertexOutput {
        var out: VertexOutput;
        
        // Scale vertex position by instance scale
        let scaledPos = vertex.position * instance.scale;
        
        // Translate to instance position
        let worldPos = vec4f(scaledPos + instance.instancePos, 1.0);
        
        // Transform to clip space
        let viewPos = uniforms.view * worldPos;
        out.position = uniforms.projection * viewPos;
        
        // Pass normal (for lighting) and amount (for color)
        out.worldNormal = vertex.normal;
        out.amount = instance.amount;
        
        return out;
      }
      
      // Fragment shader: Color + transparency based on amount (green → yellow → red)
      @fragment
      fn fs_main(in: VertexOutput) -> @location(0) vec4f {
        // 🔧 FIX: amount 已經是標準化值 (0-1)，無需再除以 100
        let t = clamp(in.amount, 0.0, 1.0);

        // Color mapping: green (t=1) → yellow (t=0.5) → red (t=0)
        var color: vec3f;
        if (t > 0.5) {
          // High amount: green → yellow
          let s = (t - 0.5) * 2.0;
          color = mix(vec3f(1.0, 1.0, 0.0), vec3f(0.0, 1.0, 0.0), s);
        } else {
          // Low amount: yellow → red
          let s = t * 2.0;
          color = mix(vec3f(1.0, 0.0, 0.0), vec3f(1.0, 1.0, 0.0), s);
        }

        // Simple directional lighting
        let lightDir = normalize(vec3f(1.0, 1.0, 1.0));
        let diffuse = max(dot(in.worldNormal, lightDir), 0.3);

        // 透明度隨 amount 下降而下降，避免資源耗盡時仍維持高不透明度
        // t=1.0 -> 0.55, t=0.0 -> 0.12
        let alpha = 0.12 + t * 0.43;

        return vec4f(color * diffuse, alpha);
      }
    `;
  }
  
  /**
   * WGSL Shader for Velocity Vectors
   */
  private getVelocityVectorShaderCode(): string {
    return `
      // Uniforms (view + projection matrices)
      struct Uniforms {
        view: mat4x4f,
        projection: mat4x4f,
      };
      @group(0) @binding(0) var<uniform> uniforms: Uniforms;
      
      // Vertex input
      struct VertexInput {
        @location(0) position: vec3f,
      };
      
      // Vertex output
      struct VertexOutput {
        @builtin(position) position: vec4f,
      };
      
      // Vertex shader: Transform velocity vector endpoints
      @vertex
      fn vs_main(in: VertexInput) -> VertexOutput {
        var out: VertexOutput;
        
        let worldPos = vec4f(in.position, 1.0);
        let viewPos = uniforms.view * worldPos;
        out.position = uniforms.projection * viewPos;
        
        return out;
      }
      
      // Fragment shader: Yellow/orange color for velocity vectors
      @fragment
      fn fs_main(in: VertexOutput) -> @location(0) vec4f {
        // Bright yellow-orange color with slight transparency
        return vec4f(1.0, 0.8, 0.2, 0.8);
      }
    `;
  }
  
  /**
   * WGSL Shader for Group Boundary Spheres
   */
  private getGroupSphereShaderCode(): string {
    return `
      // Uniforms (view + projection matrices)
      struct Uniforms {
        view: mat4x4f,
        projection: mat4x4f,
      };
      @group(0) @binding(0) var<uniform> uniforms: Uniforms;
      
      // Vertex input (sphere geometry)
      struct VertexInput {
        @location(0) position: vec3f,
        @location(1) normal: vec3f,
      };
      
      // Instance input (group data)
      struct InstanceInput {
        @location(2) instancePos: vec3f,  // Group centroid
        @location(3) scale: f32,          // Group radius
        @location(4) groupId: u32,        // Group ID for color
        @location(5) isSelected: f32,     // 1.0 if selected, 0.0 otherwise
      };
      
      // Vertex output
      struct VertexOutput {
        @builtin(position) position: vec4f,
        @location(0) worldNormal: vec3f,
        @location(1) groupId: u32,
        @location(2) isSelected: f32,
      };
      
      // HSL to RGB conversion (same as particle shader)
      fn hsl_to_rgb(h: f32, s: f32, l: f32) -> vec3f {
        let c = (1.0 - abs(2.0 * l - 1.0)) * s;
        let x = c * (1.0 - abs((h * 6.0) % 2.0 - 1.0));
        let m = l - c / 2.0;
        
        var rgb = vec3f(0.0);
        let h6 = h * 6.0;
        if (h6 < 1.0) {
          rgb = vec3f(c, x, 0.0);
        } else if (h6 < 2.0) {
          rgb = vec3f(x, c, 0.0);
        } else if (h6 < 3.0) {
          rgb = vec3f(0.0, c, x);
        } else if (h6 < 4.0) {
          rgb = vec3f(0.0, x, c);
        } else if (h6 < 5.0) {
          rgb = vec3f(x, 0.0, c);
        } else {
          rgb = vec3f(c, 0.0, x);
        }
        
        return rgb + vec3f(m);
      }
      
      // Hash function for group_id -> color (same as particle shader)
      fn group_to_color(group_id: u32) -> vec3f {
        let seed = f32(group_id) * 0.618033988749895; // Golden ratio
        let hue = fract(seed);
        let saturation = 0.7;
        let lightness = 0.6;
        return hsl_to_rgb(hue, saturation, lightness);
      }
      
      // Vertex shader: Transform sphere with instancing
      @vertex
      fn vs_main(vertex: VertexInput, instance: InstanceInput) -> VertexOutput {
        var out: VertexOutput;
        
        // Scale vertex position by instance scale
        let scaledPos = vertex.position * instance.scale;
        
        // Translate to instance position
        let worldPos = vec4f(scaledPos + instance.instancePos, 1.0);
        
        // Transform to clip space
        let viewPos = uniforms.view * worldPos;
        out.position = uniforms.projection * viewPos;
        
        // Pass normal, group ID, and selection state
        out.worldNormal = vertex.normal;
        out.groupId = instance.groupId;
        out.isSelected = instance.isSelected;
        
        return out;
      }
      
      // Fragment shader: Color based on group ID with high transparency
      // Selected groups are brighter and more opaque
      @fragment
      fn fs_main(in: VertexOutput) -> @location(0) vec4f {
        // Get group color
        let color = group_to_color(in.groupId);
        
        // Simple directional lighting
        let lightDir = normalize(vec3f(1.0, 1.0, 1.0));
        let diffuse = max(dot(in.worldNormal, lightDir), 0.3);
        
        // 如果選中，增加亮度和不透明度
        var finalColor = color * diffuse;
        var alpha = 0.2;
        
        if (in.isSelected > 0.5) {
          // 選中的群組：更亮、更不透明
          finalColor = finalColor * 1.5; // 提高亮度 50%
          alpha = 0.5; // 提高透明度
        }
        
        return vec4f(finalColor, alpha);
      }
    `;
  }
  
  /**
   * WGSL Shader for Group Velocity Arrows
   */
  private getGroupVelocityArrowShaderCode(): string {
    return `
      // Uniforms (view + projection matrices)
      struct Uniforms {
        view: mat4x4f,
        projection: mat4x4f,
      };
      @group(0) @binding(0) var<uniform> uniforms: Uniforms;
      
      // Vertex input
      struct VertexInput {
        @location(0) position: vec3f,
        @location(1) groupId: u32,
      };
      
      // Vertex output
      struct VertexOutput {
        @builtin(position) position: vec4f,
        @location(0) @interpolate(flat) groupId: u32,
      };
      
      // HSL to RGB conversion (same as other shaders)
      fn hsl_to_rgb(h: f32, s: f32, l: f32) -> vec3f {
        let c = (1.0 - abs(2.0 * l - 1.0)) * s;
        let x = c * (1.0 - abs((h * 6.0) % 2.0 - 1.0));
        let m = l - c / 2.0;
        
        var rgb = vec3f(0.0);
        let h6 = h * 6.0;
        if (h6 < 1.0) {
          rgb = vec3f(c, x, 0.0);
        } else if (h6 < 2.0) {
          rgb = vec3f(x, c, 0.0);
        } else if (h6 < 3.0) {
          rgb = vec3f(0.0, c, x);
        } else if (h6 < 4.0) {
          rgb = vec3f(0.0, x, c);
        } else if (h6 < 5.0) {
          rgb = vec3f(x, 0.0, c);
        } else {
          rgb = vec3f(c, 0.0, x);
        }
        
        return rgb + vec3f(m);
      }
      
      // Hash function for group_id -> color
      fn group_to_color(group_id: u32) -> vec3f {
        let seed = f32(group_id) * 0.618033988749895; // Golden ratio
        let hue = fract(seed);
        let saturation = 0.8;
        let lightness = 0.7; // Brighter for arrows
        return hsl_to_rgb(hue, saturation, lightness);
      }
      
      // Vertex shader: Transform arrow endpoints
      @vertex
      fn vs_main(in: VertexInput) -> VertexOutput {
        var out: VertexOutput;
        
        let worldPos = vec4f(in.position, 1.0);
        let viewPos = uniforms.view * worldPos;
        out.position = uniforms.projection * viewPos;
        out.groupId = in.groupId;
        
        return out;
      }
      
      // Fragment shader: Color based on group ID (matching group boundaries)
      @fragment
      fn fs_main(in: VertexOutput) -> @location(0) vec4f {
        let color = group_to_color(in.groupId);
        return vec4f(color, 0.9); // High opacity for visibility
      }
    `;
  }
}
