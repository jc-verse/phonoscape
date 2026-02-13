function data = mdp_AggVel(data, varargin)
%MDP_AGGVEL  - MVIEW dataproc that appends aggregate velocity computed across specified trajectories
%
%	varargin{1} - cellstr list of trajectories, followed by optional low-pass Fc (default none)
%
% appends AGGVEL, the aggregate velocity computed across the (optionally filtered) spatial components
% of the specified trajectories (cm/sec)
%
% because this takes arguments (the cellstr array of trajectories) it must be embedded as
% a cell element within the DPROC list (i.e., nested within {})
%
% usage example:  mview(...,'DPROC',{{'mdp_AggVel',{'TR','TB','TT'}}}, ...)
% LP filtering @5Hz: mview(...,'DPROC',{{'mdp_AggVel',{'TR','TB','TT', 5}}}, ...)

% mkt 11/15

names = upper({data.NAME});
traj = varargin(1:end-1);		% last arg is {pal,phar,labs}
filt = [];
if ~ischar(traj{end}),
	filt = traj{end};
	traj(end) = [];
end;

idx = [];
for ti = 1 : length(traj),
	k = find(strcmpi(traj{ti},names));
	if isempty(k),
		error('%s not found in dataset', traj{ti});
	end;
	idx = [idx , k];
end;
[d,sr,names] = ArrayFromStruct(data(idx));	% [nSamps x X,Y,Z x nTraj]
d = double(d(:,1:3,:));

% filter
if ~isempty(filt),
	[b,a] = butter(3,filt*2/sr,'low');
	for k = 1 : size(d,3),
		ds = d(:,:,k);
		fq = NaN(size(ds));
		bad = find(isnan(ds));
		good = find(all(~isnan(ds),2));
		if isempty(good), 					% all bad -- give up
			error('missing data in all %d frames of %s', size(ds,1), names{k});
		end;
		if isempty(bad),
			qq = ds;						% none are missing
		else,								% interpolate across missing data points for LP filtering
			qq = interp1(good,ds(good,:),linspace(good(1),good(end),good(end)-good(1)+1)','pchip');
			fprintf('missing data in %d / %d frames of %s\n', sum(any(isnan(ds),2)), size(ds,1), names{k});
		end;
		fq(good(1):good(end),:) = filtfilt(b,a,qq);
		fq(bad) = NaN;						% restore missing status
		d(:,:,k) = fq;
	end;
end;

% compute velocity
data(end+1) = data(idx(1));
data(end).NAME = 'AGGVEL';
d = reshape(d,[size(d,1),3*size(d,3)]);		% [nSamps x X1,Y1,Z1, ... Xn,Yn,Zn]
d = sr * [diff(d([1 3],:)) ; d(3:end,:) - d(1:end-2,:) ; diff(d([end-2 end],:))] ./ 20;	% cm/sec
data(end).SIGNAL = sqrt(sum(d.^2,2));
minS = min(data(end).SIGNAL);
maxS = max(data(end).SIGNAL);
spread = maxS - minS;
data(end).SPREAD = [minS-spread*.1 maxS+spread*.1];	% pad
data(end).NCOMPS = 1;
