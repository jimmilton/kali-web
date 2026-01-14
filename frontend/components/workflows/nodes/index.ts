export { ToolNode } from './tool-node';
export { ConditionNode } from './condition-node';
export { DelayNode } from './delay-node';
export { NotificationNode } from './notification-node';
export { ParallelNode } from './parallel-node';
export { LoopNode } from './loop-node';
export { ManualNode } from './manual-node';

import { ToolNode } from './tool-node';
import { ConditionNode } from './condition-node';
import { DelayNode } from './delay-node';
import { NotificationNode } from './notification-node';
import { ParallelNode } from './parallel-node';
import { LoopNode } from './loop-node';
import { ManualNode } from './manual-node';

export const nodeTypes = {
  tool: ToolNode,
  condition: ConditionNode,
  delay: DelayNode,
  notification: NotificationNode,
  parallel: ParallelNode,
  loop: LoopNode,
  manual: ManualNode,
};
