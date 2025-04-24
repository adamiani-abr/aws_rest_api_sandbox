# Autoscaling rules to scale down ECS services to 0 count at 6 PM and scale up to 1 count at 8 AM EST

aws application-autoscaling register-scalable-target `
  --service-namespace ecs `
  --resource-id service/cluster-name/service-name `
  --scalable-dimension ecs:service:DesiredCount `
  --min-capacity 0 `
  --max-capacity 1

aws application-autoscaling put-scheduled-action `
  --service-namespace ecs `
  --scheduled-action-name scale-down-at-night `
  --resource-id service/cluster-name/service-name `
  --scalable-dimension ecs:service:DesiredCount `
  --schedule "cron(0 23 * * ? *)" `
  --scalable-target-action MinCapacity=0,MaxCapacity=0

aws application-autoscaling put-scheduled-action `
  --service-namespace ecs `
  --scheduled-action-name scale-up-in-morning `
  --resource-id service/cluster-name/service-name `
  --scalable-dimension ecs:service:DesiredCount `
  --schedule "cron(0 13 * * ? *)" `
  --scalable-target-action MinCapacity=1,MaxCapacity=1
